"""Background job processing logic."""
import asyncio
from typing import Any

from .genbank_parser import parse_genbank_record, parse_genbank_batch
from .job_store import get_job_store
from .models import JobStatus
from .ncbi_client import NCBIClient


async def process_query_job(job_id: str, input_data: dict[str, Any]) -> None:
    """
    Process a free-text query job in the background.

    Args:
        job_id: Job identifier
        input_data: Job input parameters (organism, keywords, filters, limit)
    """
    job_store = get_job_store()
    
    try:
        await job_store.update_job_status(job_id, JobStatus.RUNNING)
        
        organism = input_data["organism"]
        keywords = input_data.get("keywords", [])
        filters = input_data.get("filters", {})
        limit = input_data.get("limit", 20)
        
        # Build search term
        search_terms = [f"{organism}[Organism]"]
        if keywords:
            if isinstance(keywords, str):
                keywords = [keywords]
            for kw in keywords:
                search_terms.append(f"{kw}[All Fields]")
        
        # Add filters
        if filters.get("assembly_level"):
            levels = filters["assembly_level"]
            if isinstance(levels, list) and levels:
                level_str = levels[0]  # Use first for now
                search_terms.append(f'"{level_str}"[Assembly Level]')
        
        # Note: refseq[filter] doesn't work in assembly database
        # RefSeq vs GenBank is determined by the assembly accession prefix (GCF_ vs GCA_)
        # We'll filter for RefSeq after retrieving results
        
        if filters.get("latest_only", True):
            search_terms.append("latest[filter]")
        
        term = " AND ".join(search_terms)
        
        async with NCBIClient() as client:
            # Search assemblies
            search_resp = await client.esearch(db="assembly", term=term, retmax=limit)
            search_data = search_resp.json()
            
            id_list = search_data.get("esearchresult", {}).get("idlist", [])
            
            if not id_list:
                await job_store.add_job_error(job_id, "No assemblies found matching criteria")
                await job_store.update_job_status(job_id, JobStatus.SUCCEEDED)
                return
            
            # Get assembly summaries
            summary_resp = await client.esummary(db="assembly", id=id_list)
            summary_data = summary_resp.json()
            
            result = summary_data.get("result", {})
            
            # Filter for RefSeq if requested (GCF_ prefix)
            prefer_refseq = filters.get("source_db_preference") == "RefSeq"
            filtered_ids = []
            
            for uid in id_list:
                if uid == "uids":
                    continue
                assembly_doc = result.get(uid, {})
                assembly_acc = assembly_doc.get("assemblyaccession", "")
                
                # Apply RefSeq filter if requested
                if prefer_refseq and not assembly_acc.startswith("GCF_"):
                    continue
                
                filtered_ids.append(uid)
                if len(filtered_ids) >= limit:
                    break
            
            if not filtered_ids:
                await job_store.add_job_error(job_id, "No assemblies found after filtering")
                await job_store.update_job_status(job_id, JobStatus.SUCCEEDED)
                return
            
            # Update progress total
            await job_store.update_job_progress(job_id, total=len(filtered_ids))

            # Bounded concurrency for faster processing
            from .config import get_settings
            concurrency = max(1, get_settings().ncbi_concurrency)
            sem = asyncio.Semaphore(concurrency)

            async def resolve_primary(uid: str):
                if uid == "uids":
                    return None
                async with sem:
                    assembly_doc = result.get(uid, {})
                    assembly_acc = assembly_doc.get("assemblyaccession", "")
                    try:
                        # Link to nuccore to get representative sequence
                        link_resp = await client.elink(
                            dbfrom="assembly",
                            db="nuccore",
                            id=uid,
                            linkname="assembly_nuccore_refseq",
                        )
                        link_data = link_resp.json()
                        nuccore_ids: list[str] = []
                        linksets = link_data.get("linksets", [])
                        if linksets:
                            linksetdbs = linksets[0].get("linksetdbs", [])
                            if linksetdbs:
                                nuccore_ids = linksetdbs[0].get("links", [])
                        if not nuccore_ids:
                            await job_store.add_job_error(job_id, f"No nuccore link for {assembly_acc}")
                            return None
                        return (nuccore_ids[0], assembly_doc)
                    except Exception as e:
                        await job_store.add_job_error(job_id, f"Error linking assembly {assembly_acc}: {str(e)}")
                        return None

            # Resolve all primary nuccore IDs concurrently
            resolved = await asyncio.gather(*[resolve_primary(uid) for uid in filtered_ids])
            pairs = [(nid, doc) for nid, doc in resolved if nid is not None]  # type: ignore[misc]
            if not pairs:
                await job_store.update_job_status(job_id, JobStatus.SUCCEEDED)
                return

            # Batch efetch and parse
            from .config import get_settings
            batch_size = max(1, get_settings().ncbi_batch_size)
            gb_cache: dict[str, dict[str, Any]] = {}

            for i in range(0, len(pairs), batch_size):
                batch = pairs[i : i + batch_size]
                # Identify which IDs need fetching (not cached)
                ids_to_fetch = [nid for nid, _ in batch if nid not in gb_cache]
                parsed_list: list[dict[str, Any]] = []
                if ids_to_fetch:
                    gb_resp = await client.efetch(db="nuccore", id=ids_to_fetch, rettype="gb", retmode="text")
                    gb_text = gb_resp.text
                    parsed_list = await asyncio.to_thread(parse_genbank_batch, gb_text)
                # Map parsed records back to ids in order
                idx = 0
                for nid, assembly_doc in batch:
                    parsed = gb_cache.get(nid)
                    if parsed is None:
                        if idx < len(parsed_list):
                            parsed = parsed_list[idx]
                            idx += 1
                            if parsed:
                                gb_cache[nid] = parsed
                    if parsed:
                        enriched = dict(parsed)
                        enriched["assembly"] = {
                            "accession": assembly_doc.get("assemblyaccession", ""),
                            "name": assembly_doc.get("assemblyname", ""),
                            "level": assembly_doc.get("assemblystatus", ""),
                            "refseq_category": assembly_doc.get("refseq_category", ""),
                            "submitter": assembly_doc.get("submitter", ""),
                            "date": assembly_doc.get("seqreleasedate", ""),
                        }
                        await job_store.add_job_result(job_id, enriched)
                    else:
                        await job_store.add_job_error(job_id, "Failed to parse GenBank record")
            
        await job_store.update_job_status(job_id, JobStatus.SUCCEEDED)
    
    except Exception as e:
        await job_store.add_job_error(job_id, f"Job failed: {str(e)}")
        await job_store.update_job_status(job_id, JobStatus.FAILED)


async def process_accession_job(job_id: str, input_data: dict[str, Any]) -> None:
    """
    Process an accession list job in the background.

    Args:
        job_id: Job identifier
        input_data: Job input parameters (accessions, filters)
    """
    job_store = get_job_store()
    
    try:
        await job_store.update_job_status(job_id, JobStatus.RUNNING)
        
        accessions = input_data["accessions"]

        # Set total for progress
        await job_store.update_job_progress(job_id, total=len(accessions))

        async with NCBIClient() as client:
            from .config import get_settings
            concurrency = max(1, get_settings().ncbi_concurrency)
            sem = asyncio.Semaphore(concurrency)

            async def resolve_accession(accession: str):
                async with sem:
                    try:
                        # Detect accession type
                        if accession.startswith("GCF_") or accession.startswith("GCA_"):
                            # Assembly accession - search by accession
                            search_resp = await client.esearch(
                                db="assembly",
                                term=f"{accession}[Assembly Accession]",
                                retmax=1,
                            )
                            search_data = search_resp.json()
                            assembly_ids = search_data.get("esearchresult", {}).get("idlist", [])
                            if not assembly_ids:
                                await job_store.add_job_error(job_id, f"Assembly not found: {accession}")
                                return None
                            # Get assembly summary
                            summary_resp = await client.esummary(db="assembly", id=assembly_ids[0])
                            summary_data = summary_resp.json()
                            assembly_doc = summary_data.get("result", {}).get(assembly_ids[0], {})
                            # Link to nuccore
                            link_resp = await client.elink(
                                dbfrom="assembly",
                                db="nuccore",
                                id=assembly_ids[0],
                                linkname="assembly_nuccore_refseq",
                            )
                            link_data = link_resp.json()
                            nuccore_ids = []
                            linksets = link_data.get("linksets", [])
                            if linksets:
                                linksetdbs = linksets[0].get("linksetdbs", [])
                                if linksetdbs:
                                    nuccore_ids = linksetdbs[0].get("links", [])
                            if not nuccore_ids:
                                await job_store.add_job_error(job_id, f"No nuccore link for {accession}")
                                return None
                            return (nuccore_ids[0], assembly_doc)
                        else:
                            # Nuccore accession (NC_, NZ_, CP_, etc.) -- fetch directly
                            return (accession, None)
                    except Exception as e:
                        await job_store.add_job_error(job_id, f"Error resolving {accession}: {str(e)}")
                        return None

            resolved = await asyncio.gather(*[resolve_accession(a) for a in accessions])
            pairs = [(nid, doc) for nid, doc in resolved if nid is not None]  # type: ignore[misc]
            if not pairs:
                await job_store.update_job_status(job_id, JobStatus.SUCCEEDED)
                return

            from .config import get_settings
            batch_size = max(1, get_settings().ncbi_batch_size)
            gb_cache: dict[str, dict[str, Any]] = {}

            for i in range(0, len(pairs), batch_size):
                batch = pairs[i : i + batch_size]
                ids_to_fetch = [nid for nid, _ in batch if nid not in gb_cache]
                parsed_list: list[dict[str, Any]] = []
                if ids_to_fetch:
                    gb_resp = await client.efetch(db="nuccore", id=ids_to_fetch, rettype="gb", retmode="text")
                    gb_text = gb_resp.text
                    parsed_list = await asyncio.to_thread(parse_genbank_batch, gb_text)
                idx = 0
                for nid, assembly_doc in batch:
                    parsed = gb_cache.get(nid)
                    if parsed is None:
                        if idx < len(parsed_list):
                            parsed = parsed_list[idx]
                            idx += 1
                            if parsed:
                                gb_cache[nid] = parsed
                    if parsed:
                        enriched = dict(parsed)
                        if assembly_doc:
                            enriched["assembly"] = {
                                "accession": assembly_doc.get("assemblyaccession", ""),
                                "name": assembly_doc.get("assemblyname", ""),
                                "level": assembly_doc.get("assemblystatus", ""),
                                "refseq_category": assembly_doc.get("refseq_category", ""),
                            }
                        else:
                            enriched.setdefault("assembly", {"accession": None, "name": None, "level": None})
                        await job_store.add_job_result(job_id, enriched)
                    else:
                        await job_store.add_job_error(job_id, f"Failed to parse GenBank for {nid}")
        
        await job_store.update_job_status(job_id, JobStatus.SUCCEEDED)
    
    except Exception as e:
        await job_store.add_job_error(job_id, f"Job failed: {str(e)}")
        await job_store.update_job_status(job_id, JobStatus.FAILED)
