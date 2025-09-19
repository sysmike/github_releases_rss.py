"""Script that fetches recent github releases and puts them in a RSS file"""

import datetime
import sys
import xml.etree.ElementTree as ET
import requests
import markdown

# === CONFIGURATION ===
GITHUB_USERNAME = "your_username"
GITHUB_TOKEN = "ghp_your_personal_access_token"
FEED_LIMIT = 25  # Max number of releases in the feed

# === HEADERS ===
headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "X-GitHub-Api-Version": "2022-11-28"
}

# === STEP 1: Get Starred Repositories ===
STARRED_URL = f"https://api.github.com/users/{GITHUB_USERNAME}/starred"
STARRED_REPOS = []
PAGE = 1

print("Fetching starred repositories...")

while True:
    PAGED_URL = f"{STARRED_URL}?per_page=100&page={PAGE}"
    response = requests.get(PAGED_URL, headers=headers, timeout=10)
    if response.status_code != 200:
        print(f"Error fetching starred repos: {response.status_code}")
        sys.exit(1)

    data = response.json()
    if not data:
        break

    STARRED_REPOS.extend(data)
    PAGE += 1

print(f"Found {len(STARRED_REPOS)} starred repositories.")

# === STEP 2: Get Latest Releases ===
releases = []

print("Fetching releases from starred repos...")

for repo in STARRED_REPOS:
    full_name = repo["full_name"]
    RELEASES_URL = f"https://api.github.com/repos/{full_name}/releases/latest"
    r = requests.get(RELEASES_URL, headers=headers, timeout=10)

    if r.status_code == 200:
        release = r.json()
        if release.get("published_at"):
            releases.append({
                "repo": full_name,
                "tag": release["tag_name"],
                "title": release["name"] or release["tag_name"],
                "url": release["html_url"],
                "published_at": release["published_at"],
                "body": release.get("body", "")
            })

# Sort by published date (descending)
releases = sorted(releases, key=lambda x: x["published_at"], reverse=True)[:FEED_LIMIT]

print(f"Found {len(releases)} latest releases.")

# === STEP 3: Build Atom Feed ===
feed = ET.Element("feed", xmlns="http://www.w3.org/2005/Atom")
ET.SubElement(feed, "title").text = f"Releases of {GITHUB_USERNAME}'s Starred Repos"
ET.SubElement(feed, "updated").text = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
ET.SubElement(feed, "id").text = f"https://github.com/{GITHUB_USERNAME}/starred"

for rel in releases:
    entry = ET.SubElement(feed, "entry")
    ET.SubElement(entry, "title").text = f"{rel['repo']} – {rel['title']}"
    ET.SubElement(entry, "link", href=rel['url'])
    ET.SubElement(entry, "id").text = rel['url']
    ET.SubElement(entry, "updated").text = rel['published_at']

    # Format body using Markdown → HTML
    raw_body = rel["body"] or ""
    md_html = markdown.markdown(raw_body)

    # Optional truncate if too long
    if len(md_html) > 5000:
        md_html = md_html[:5000] + "<p>... (truncated)</p>"

    content = ET.SubElement(entry, "content", type="html")
    content.text = f"{md_html}"

# === STEP 4: Save to File ===
tree = ET.ElementTree(feed)
ET.indent(tree, space="  ", level=0)
tree.write("github.xml", encoding="utf-8", xml_declaration=True)

print("Feed saved to 'github.xml'")
