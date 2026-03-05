#!/usr/bin/env python3
"""
Delete all customer profiles from an Amazon Connect Customer Profiles domain.
Strategy: enumerate unique LastName values, search each to collect all profile IDs, then bulk delete.
Usage: PYTHONHOME= PYTHONPATH= /usr/bin/python3 scripts/delete-all-profiles.py
"""

import boto3
import time
import argparse
import functools
from concurrent.futures import ThreadPoolExecutor, as_completed

print = functools.partial(print, flush=True)

DOMAIN = "amazon-connect-loguclyd-demo"
REGION = "us-east-1"


def get_all_attribute_values(client, domain, attribute_name):
    """Get all unique values for a profile attribute."""
    values = []
    next_token = None
    while True:
        kwargs = {
            "DomainName": domain,
            "AttributeName": attribute_name,
        }
        if next_token:
            kwargs["NextToken"] = next_token
        resp = client.list_profile_attribute_values(**kwargs)
        for item in resp.get("Items", []):
            values.append(item["Value"])
        next_token = resp.get("NextToken")
        if not next_token:
            break
    return values


def search_all_by_name(client, domain, first_name, last_name):
    """Search for all profiles matching a first+last name combo."""
    profile_ids = []
    full_name = f"{first_name} {last_name}"
    next_token = None
    while True:
        kwargs = {
            "DomainName": domain,
            "KeyName": "_fullName",
            "Values": [full_name],
            "MaxResults": 100,
        }
        if next_token:
            kwargs["NextToken"] = next_token
        resp = client.search_profiles(**kwargs)
        for item in resp.get("Items", []):
            profile_ids.append(item["ProfileId"])
        next_token = resp.get("NextToken")
        if not next_token or not resp.get("Items"):
            break
    return profile_ids


def delete_profile(client, domain, profile_id):
    """Delete a single profile."""
    try:
        client.delete_profile(DomainName=domain, ProfileId=profile_id)
        return True, None
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description="Delete all Customer Profiles")
    parser.add_argument("--domain", default=DOMAIN, help=f"Domain name (default: {DOMAIN})")
    parser.add_argument("--region", default=REGION, help=f"AWS region (default: {REGION})")
    parser.add_argument("--threads", type=int, default=10, help="Parallel threads (default: 10)")
    parser.add_argument("--dry-run", action="store_true", help="Count profiles but don't delete")
    args = parser.parse_args()

    client = boto3.client("customer-profiles", region_name=args.region)

    # Get current count
    domain_info = client.get_domain(DomainName=args.domain)
    current_count = domain_info.get("Stats", {}).get("ProfileCount", 0)
    print(f"📊 Domain '{args.domain}' has {current_count} profiles")

    # Step 1: Get all unique first names and last names
    print(f"\n🔍 Enumerating unique names...")
    first_names = get_all_attribute_values(client, args.domain, "FirstName")
    last_names = get_all_attribute_values(client, args.domain, "LastName")
    print(f"   Found {len(first_names)} unique first names, {len(last_names)} unique last names")
    print(f"   Will search up to {len(first_names) * len(last_names)} name combinations")

    # Step 2: Search every first+last combo to collect all profile IDs
    print(f"\n🔍 Collecting profile IDs by name search...")
    profile_ids = set()
    combos_searched = 0
    total_combos = len(first_names) * len(last_names)

    for last in last_names:
        for first in first_names:
            ids = search_all_by_name(client, args.domain, first, last)
            for pid in ids:
                profile_ids.add(pid)
            combos_searched += 1

        # Progress per last name batch
        print(f"   Searched {combos_searched}/{total_combos} combos — found {len(profile_ids)} unique profiles so far (last: {last})")

        # Early exit if we've found them all
        if len(profile_ids) >= current_count:
            print(f"   ✅ Found all {current_count} profiles, stopping search early")
            break

    print(f"   ✅ Collected {len(profile_ids)} unique profile IDs")

    if args.dry_run:
        print(f"\n🏁 Dry run complete. Would delete {len(profile_ids)} profiles.")
        return

    if not profile_ids:
        print("   Nothing to delete!")
        return

    # Step 3: Delete all profiles
    print(f"\n🗑️  Deleting {len(profile_ids)} profiles ({args.threads} threads)...")
    start_time = time.time()
    success = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = {
            executor.submit(delete_profile, client, args.domain, pid): pid
            for pid in profile_ids
        }
        for future in as_completed(futures):
            ok, error = future.result()
            if ok:
                success += 1
            else:
                failed += 1
                if failed <= 5:
                    pid = futures[future]
                    print(f"   ❌ Failed to delete {pid}: {error}")

            total = success + failed
            if total % 200 == 0:
                elapsed = time.time() - start_time
                rate = total / elapsed if elapsed > 0 else 0
                print(f"   Progress: {total}/{len(profile_ids)} ({rate:.0f}/sec) — ✅ {success} ❌ {failed}")

    elapsed = time.time() - start_time
    print(f"\n============================================")
    print(f"🎉 Deletion Complete!")
    print(f"   ✅ Deleted: {success}")
    print(f"   ❌ Failed:  {failed}")
    print(f"   ⏱️  Time:    {elapsed:.1f}s")
    print(f"============================================")

    # Verify
    domain_info = client.get_domain(DomainName=args.domain)
    remaining = domain_info.get("Stats", {}).get("ProfileCount", "?")
    print(f"\n📊 Remaining profiles: {remaining}")
    print(f"   (Note: count may take a moment to update)")


if __name__ == "__main__":
    main()
