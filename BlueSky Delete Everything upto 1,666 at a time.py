import requests
import time

# Your Bluesky credentials
handle = 'username.bsky.social'
app_password = 'xxxx-xxxx-xxxx-xxxx'

def get_session():
    url = 'https://bsky.social/xrpc/com.atproto.server.createSession'
    payload = {
        'identifier': handle,
        'password': app_password
    }
    resp = requests.post(url, json=payload)
    resp.raise_for_status()
    data = resp.json()
    return data['accessJwt'], data['did']

def get_author_feed(jwt, actor, limit=100, cursor=None):
    url = 'https://bsky.social/xrpc/app.bsky.feed.getAuthorFeed'
    headers = {
        'Authorization': f'Bearer {jwt}'
    }
    params = {
        'actor': actor,
        'limit': limit
    }
    if cursor:
        params['cursor'] = cursor
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    return resp.json()

def delete_record(jwt, did, rkey, collection='app.bsky.feed.post'):
    url = 'https://bsky.social/xrpc/com.atproto.repo.deleteRecord'
    headers = {
        'Authorization': f'Bearer {jwt}',
        'Content-Type': 'application/json'
    }
    payload = {
        'repo': did,
        'collection': collection,
        'rkey': rkey
    }
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code == 200:
        print(f"✅ Deleted: {rkey} ({collection})")
    else:
        print(f"❌ Failed to delete {rkey}: {resp.status_code} - {resp.text}")

def list_reposts(jwt, did, limit=100, cursor=None):
    url = 'https://bsky.social/xrpc/com.atproto.repo.listRecords'
    headers = {'Authorization': f'Bearer {jwt}'}
    params = {
        'repo': did,
        'collection': 'app.bsky.feed.repost',
        'limit': limit
    }
    if cursor:
        params['cursor'] = cursor
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    return resp.json().get('records', []), resp.json().get('cursor')

if __name__ == '__main__':
    jwt, did = get_session()
    total_deleted = 0
    delete_limit = 1666

    print(f"\n🧹 Deleting up to {delete_limit} total posts and reposts from your feed...\n")

    # STEP 1 — Delete original posts from your feed
    cursor = None
    while total_deleted < delete_limit:
        feed_data = get_author_feed(jwt, handle, limit=100, cursor=cursor)
        posts = feed_data.get('feed', [])
        cursor = feed_data.get('cursor')

        if not posts:
            print("📭 No more original posts found.")
            break

        for item in posts:
            # Skip reposts made by others (that appear in your feed)
            if item.get('reason', {}).get('$type') == 'app.bsky.feed.defs#reasonRepost':
                print("↩️ Skipping reposted content (not your original post)")
                continue

            post = item.get('post', {})
            uri = post.get('uri')
            if not uri:
                continue
            rkey = uri.split('/')[-1]
            text = post.get('record', {}).get('text', '[No text]')
            print(f"📝 Deleting post: {text[:60]!r} → rkey={rkey}")

            delete_record(jwt, did, rkey)
            total_deleted += 1
            time.sleep(0.4)

            if total_deleted >= delete_limit:
                break

        if not cursor:
            break

    # STEP 2 — Delete your reposts (from your repo)
    print("\n🔄 Deleting your reposts...\n")
    cursor = None
    while total_deleted < delete_limit:
        reposts, cursor = list_reposts(jwt, did, cursor=cursor)
        if not reposts:
            print("📭 No more reposts found.")
            break

        for repost in reposts:
            uri = repost.get('uri')
            rkey = repost.get('rkey') or uri.split('/')[-1]
            delete_record(jwt, did, rkey, collection='app.bsky.feed.repost')
            total_deleted += 1
            time.sleep(0.4)

            if total_deleted >= delete_limit:
                break

        if not cursor:
            break

    print(f"\n✅ Finished. Total deleted (posts + reposts): {total_deleted}")
