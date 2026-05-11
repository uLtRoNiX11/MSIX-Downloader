import os
import re
import sys

from curl_cffi import requests


def fetch_store_links(app_id):
    url = "https://store.rg-adguard.net/api/GetFiles"

    payload = {"type": "ProductId", "url": app_id, "ring": "Retail", "lang": "en-US"}

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://store.rg-adguard.net",
        "Referer": "https://store.rg-adguard.net/",
    }

    print(f"[*] Querying Windows Update servers for App ID: {app_id}...")

    try:
        # Using impersonate="chrome" to bypass the 403 Cloudflare/WAF block
        response = requests.post(
            url, data=payload, headers=headers, impersonate="chrome", timeout=15
        )
        response.raise_for_status()
    except Exception as e:
        print(f"[!] Error connecting to the service: {e}")
        sys.exit(1)

    # Regex to extract the direct URL and the filename from the HTML response
    pattern = re.compile(r'<a href="([^"]+)"[^>]*>([^<]+)</a>')
    matches = pattern.findall(response.text)

    return matches


def download_file(url, filename):
    print(f"\n[*] Starting download for: {filename}")
    print("[*] This may take a few minutes depending on file size...")

    try:
        # Removed the 'with' block here since curl_cffi Response doesn't support it
        r = requests.get(url, stream=True, impersonate="chrome", timeout=20)
        r.raise_for_status()

        total_length = r.headers.get("content-length")

        with open(filename, "wb") as f:
            if total_length is None:
                f.write(r.content)
            else:
                dl = 0
                total_length = int(total_length)
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:  # filter out keep-alive new chunks
                        dl += len(chunk)
                        f.write(chunk)

                        done = int(50 * dl / total_length)
                        sys.stdout.write(
                            f"\r[{'=' * done}{' ' * (50 - done)}] {dl // (1024 * 1024)}MB / {total_length // (1024 * 1024)}MB"
                        )
                        sys.stdout.flush()

        print(f"\n\n[+] Successfully saved to: {os.path.abspath(filename)}")

    except Exception as e:
        print(f"\n[!] Failed to download the file: {e}")


def main():
    app_id = input("Enter the Microsoft Store App ID (e.g., 9WZDNCRFHVN5): ").strip()

    if not app_id:
        print("[!] App ID cannot be empty.")
        sys.exit(1)

    links = fetch_store_links(app_id)

    # Filter for bundles (.msixbundle or fallback to .appxbundle)
    bundles = [
        match for match in links if match[1].endswith((".msixbundle", ".appxbundle"))
    ]

    if not bundles:
        print("[-] No .msixbundle or .appxbundle found for this App ID.")
        print(
            "[-] The app might only provide individual .appx files or it might be a paid app."
        )
        sys.exit(0)

    print(f"\n[+] Found {len(bundles)} bundle(s):")
    for idx, (link, filename) in enumerate(bundles):
        print(f"    {idx + 1}. {filename}")

    # Auto-select the first bundle
    target_link, target_filename = bundles[0]

    if len(bundles) > 1:
        choice = input(
            f"\nSelect a file to download [1-{len(bundles)}] (default is 1): "
        ).strip()
        if choice.isdigit() and 1 <= int(choice) <= len(bundles):
            target_link, target_filename = bundles[int(choice) - 1]

    download_file(target_link, target_filename)


if __name__ == "__main__":
    main()
