# Sven Vestli, Athanasios Rizikianos, Leyi Hu, Klevis Nrecaj
# This is the script for our final project in the Social Computing course at the University of Zürich in the spring semester of 2026.
# Individual code sections might be labeled like [A], [B], etc. These labels are used in the report to refer to specific code sections.

from itertools import combinations
import math
import random
import json
import networkx as nx
import pandas as pd
import pickle
import time

# --- CONFIGURATION ---

random.seed(27)

TESTING = True
TEST_SHARE = .5 # So only x percent of the sample will actually be analyzed.

# Recommendations & evaluation
TOP_K = 3 #
EVALUATION_SAMPLE_SIZE = 10
DAMPING_FACTOR = 0.85

# --- CACHING STUFF ---

def _get_cache_filename(prefix, share, num_repos):
    if TESTING:
        return f"{prefix}_test_share{share}_repos{num_repos}.pkl"
    else:
        return f"{prefix}_full_repos{num_repos}.pkl"

def _get_pagerank_cache_filename(prefix, share, num_repos, damping):
    if TESTING:
        return f"{prefix}_test_share{share}_repos{num_repos}_damp{damping}.pkl"
    else:
        return f"{prefix}_full_repos{num_repos}_damp{damping}.pkl"

def save_graphs(G_weighted, G_unweighted, testing_share, num_repos):
    w_filename = _get_cache_filename("graph_weighted", testing_share, num_repos)
    u_filename = _get_cache_filename("graph_unweighted", testing_share, num_repos)
    with open(w_filename, 'wb') as f:
        pickle.dump(G_weighted, f)
    with open(u_filename, 'wb') as f:
        pickle.dump(G_unweighted, f)
    print(f"[B] Graphs cached to {w_filename} and {u_filename}")

def load_graphs(testing_share, num_repos):
    w_filename = _get_cache_filename("graph_weighted", testing_share, num_repos)
    u_filename = _get_cache_filename("graph_unweighted", testing_share, num_repos)
    try:
        with open(w_filename, 'rb') as f:
            G_weighted = pickle.load(f)
        with open(u_filename, 'rb') as f:
            G_unweighted = pickle.load(f)
        print(f"[B] Loaded cached graphs (share {testing_share}, repos {num_repos})")
        return G_weighted, G_unweighted
    except FileNotFoundError:
        print(f"[B] No cached graphs found. Building from scratch.")
        return None, None

def save_pageranks(pr_weighted, pr_unweighted, testing_share, num_repos, damping):
    w_filename = _get_pagerank_cache_filename("pagerank_weighted", testing_share, num_repos, damping)
    u_filename = _get_pagerank_cache_filename("pagerank_unweighted", testing_share, num_repos, damping)
    with open(w_filename, 'wb') as f:
        pickle.dump(pr_weighted, f)
    with open(u_filename, 'wb') as f:
        pickle.dump(pr_unweighted, f)
    print(f"[C] PageRank vectors cached to {w_filename} and {u_filename}")

def load_pageranks(testing_share, num_repos, damping):
    w_filename = _get_pagerank_cache_filename("pagerank_weighted", testing_share, num_repos, damping)
    u_filename = _get_pagerank_cache_filename("pagerank_unweighted", testing_share, num_repos, damping)
    try:
        with open(w_filename, 'rb') as f:
            pr_weighted = pickle.load(f)
        with open(u_filename, 'rb') as f:
            pr_unweighted = pickle.load(f)
        print(f"[C] Loaded cached PageRank vectors (share {testing_share}, repos {num_repos}, damping {damping})")
        return pr_weighted, pr_unweighted
    except FileNotFoundError:
        print(f"[C] No cached PageRank vectors found. Computing from scratch.")
        return None, None

# --- [A] DATA COLLECTION ---

# We've used Google BigQuery to query the data ahead of time. This is the query we've used.
# It is important to mention that this query only cares only about repositories with ...
#       ... at least 2 contributors to ensure they're valuable to our inquiry at all ...
#       ... and a maximum of 500 contributors for performance reasons
# THIS FILE HAS TO BE DOWNLOADED FROM HERE: https://drive.google.com/file/d/1FnPoayp6Adwi26fdKRTih5xm07cr2Rv6/view?usp=sharing
# AND NEEDS TO BE IN THE SAME FOLDER AS THE SCRIPT

_SQL_QUERY = """
WITH Contributions AS (
  SELECT repo_name, user_login
  FROM (
    SELECT repo.name AS repo_name, actor.login AS user_login
    FROM `githubarchive.day.202501*` 
    WHERE type IN ('PushEvent','PullRequestEvent') AND actor.login NOT LIKE '%[bot]%' AND repo.name IS NOT NULL AND actor.login IS NOT NULL
    UNION ALL
    SELECT repo.name, actor.login
    FROM `githubarchive.day.202502*` 
    WHERE type IN ('PushEvent','PullRequestEvent') AND actor.login NOT LIKE '%[bot]%' AND repo.name IS NOT NULL AND actor.login IS NOT NULL
    UNION ALL
    SELECT repo.name, actor.login
    FROM `githubarchive.day.202503*` 
    WHERE type IN ('PushEvent','PullRequestEvent') AND actor.login NOT LIKE '%[bot]%' AND repo.name IS NOT NULL AND actor.login IS NOT NULL
    UNION ALL
    SELECT repo.name, actor.login
    FROM `githubarchive.day.202504*` 
    WHERE type IN ('PushEvent','PullRequestEvent') AND actor.login NOT LIKE '%[bot]%' AND repo.name IS NOT NULL AND actor.login IS NOT NULL
    UNION ALL
    SELECT repo.name, actor.login
    FROM `githubarchive.day.202505*` 
    WHERE type IN ('PushEvent','PullRequestEvent') AND actor.login NOT LIKE '%[bot]%' AND repo.name IS NOT NULL AND actor.login IS NOT NULL
    UNION ALL
    SELECT repo.name, actor.login
    FROM `githubarchive.day.202506*` 
    WHERE type IN ('PushEvent','PullRequestEvent') AND actor.login NOT LIKE '%[bot]%' AND repo.name IS NOT NULL AND actor.login IS NOT NULL
    UNION ALL
    SELECT repo.name, actor.login
    FROM `githubarchive.day.202507*` 
    WHERE type IN ('PushEvent','PullRequestEvent') AND actor.login NOT LIKE '%[bot]%' AND repo.name IS NOT NULL AND actor.login IS NOT NULL
    UNION ALL
    SELECT repo.name, actor.login
    FROM `githubarchive.day.202508*` 
    WHERE type IN ('PushEvent','PullRequestEvent') AND actor.login NOT LIKE '%[bot]%' AND repo.name IS NOT NULL AND actor.login IS NOT NULL
    UNION ALL
    SELECT repo.name, actor.login
    FROM `githubarchive.day.202509*` 
    WHERE type IN ('PushEvent','PullRequestEvent') AND actor.login NOT LIKE '%[bot]%' AND repo.name IS NOT NULL AND actor.login IS NOT NULL
    UNION ALL
    SELECT repo.name, actor.login
    FROM `githubarchive.day.202510*` 
    WHERE type IN ('PushEvent','PullRequestEvent') AND actor.login NOT LIKE '%[bot]%' AND repo.name IS NOT NULL AND actor.login IS NOT NULL
    UNION ALL
    SELECT repo.name, actor.login
    FROM `githubarchive.day.202511*` 
    WHERE type IN ('PushEvent','PullRequestEvent') AND actor.login NOT LIKE '%[bot]%' AND repo.name IS NOT NULL AND actor.login IS NOT NULL
    UNION ALL
    SELECT repo.name, actor.login
    FROM `githubarchive.day.202512*` 
    WHERE type IN ('PushEvent','PullRequestEvent') AND actor.login NOT LIKE '%[bot]%' AND repo.name IS NOT NULL AND actor.login IS NOT NULL
  )
  GROUP BY repo_name, user_login
),
RepoSize AS (
  SELECT 
    repo_name,
    COUNT(user_login) AS contributor_count
  FROM Contributions
  GROUP BY repo_name
  HAVING contributor_count BETWEEN 2 AND 500
)
SELECT 
  c.repo_name,
  ARRAY_AGG(c.user_login ORDER BY c.user_login) AS contributors,
  rs.contributor_count
FROM Contributions c
JOIN RepoSize rs ON c.repo_name = rs.repo_name
GROUP BY c.repo_name, rs.contributor_count
ORDER BY rs.contributor_count DESC
"""

# So what is left now is only loading the data into the script.
def load_data():
    repo_map = {}
    with open('repo_map.json', 'r') as f:
        if TESTING:
            print(f"[A] TESTING MODE: Loading {TEST_SHARE * 100}% of repos (random sample)")
            for line in f:
                if line.strip() and random.random() < TEST_SHARE:
                    row = json.loads(line)
                    repo_map[row["repo_name"]] = row["contributors"]
        else:
            print("[A] Loading all repos")
            for line in f:
                if line.strip():
                    row = json.loads(line)
                    repo_map[row["repo_name"]] = row["contributors"]

    print(f"[A] Loaded {len(repo_map)} repositories")
    return repo_map


# --- [B] GRAPH CONSTRUCTION ---

# Edge weight is sum of the inverses of the logarithms of the repo size
# This is to ensure big repositories are weighed less
def build_weighted_graph(repo_map):
    G = nx.Graph()
    print("[B] Building weighted developer-developer graph...")

    for repo, contributors in repo_map.items():
        repo_size = len(contributors)
        weight_contrib = 1.0 / math.log(repo_size + 1)

        for d_i, d_j in combinations(contributors, 2):
            if G.has_edge(d_i, d_j):
                G[d_i][d_j]["weight"] += weight_contrib
                G[d_i][d_j]["shared_repos"].append(repo)
            else:
                G.add_edge(d_i, d_j, weight=weight_contrib, shared_repos=[repo])

    print(f"[B] Graph built: {G.number_of_nodes()} developers, {G.number_of_edges()} edges.")
    return G


# Unweighted graph as a baseline to compare whether our weighted method is actually useful
def build_unweighted_graph(repo_map):
    G = nx.Graph()
    from itertools import combinations
    for repo, contributors in repo_map.items():
        for d_i, d_j in combinations(contributors, 2):
            if not G.has_edge(d_i, d_j):
                G.add_edge(d_i, d_j, weight=1, shared_repos=[repo])
            else:
                G[d_i][d_j]["shared_repos"].append(repo)
    return G


# --- [C] PAGERANK ---

# Calculating the pagerank
def compute_pagerank(G, damping=DAMPING_FACTOR):
    print("[C] Computing PageRank...")
    pr = nx.pagerank(G, alpha=damping, weight="weight")
    print("[C] PageRank done.")
    return pr


# --- [D] RECOMMENDATIONS ---

# Our goal is to recommend *new* developers to work with. So we skip developers who have already worked with in a repo intentionally even though this might create some blind spots. This could be optimized in further iterations of the algorithm.
# The score is calculated like this: sum of (m in neighbors(target)) w(target,m) * w(m,j) * PR(m)
def recommend_developers(G, pr, target_developer, k=TOP_K):
    if target_developer not in G:
        print(f"[D] Developer '{target_developer}' not found in graph.")
        return []

    direct_neighbors = set(G.neighbors(target_developer))
    candidate_scores = {}

    for m in direct_neighbors:
        w_im = G[target_developer][m]["weight"]
        pr_m = pr.get(m, 0)

        for j in G.neighbors(m):
            if j == target_developer or j in direct_neighbors:
                continue
            w_mj = G[m][j]["weight"]
            contribution = w_im * w_mj * pr_m
            candidate_scores[j] = candidate_scores.get(j, 0) + contribution

    ranked = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)
    return ranked[:k]


# --- [E] EVALUATION (qualitative) ---

# To do our qualitative evaluation we save the TOP_K recommendation of for the seed_developers (once for the weighted, once for the unweighted graph) in a .csv
def evaluate(G, pr_weighted, pr_unweighted, G_unweighted, seed_developers, k=TOP_K):
    print("[E] Running evaluation...")
    rows = []

    for seed in seed_developers:
        recs_weighted = recommend_developers(G, pr_weighted, seed, k)
        recs_unweighted = recommend_developers(G_unweighted, pr_unweighted, seed, k)

        for label, recs in [("ours", recs_weighted), ("baseline", recs_unweighted)]:
            for candidate, score in recs:
                rows.append({
                    "seed": seed,
                    "candidate": candidate,
                    "metric": label,
                    "score": round(score, 8),
                    "notes": ""
                })

    return pd.DataFrame(rows)


# --- MAIN ---

def main():
    begin_time = time.time()
    # [A] Collect data
    repo_map = load_data()
    num_repos = len(repo_map)

    # Try to load cached graphs
    G_weighted, G_unweighted = load_graphs(TEST_SHARE, num_repos)

    if G_weighted is None:
        # [B] Build graphs
        G_weighted = build_weighted_graph(repo_map)
        G_unweighted = build_unweighted_graph(repo_map)
        # Save for next time
        save_graphs(G_weighted, G_unweighted, TEST_SHARE, num_repos)
    else:
        print("[B] Using cached graphs – skipping graph construction.")

    # Try to load cached PageRank vectors
    pr_weighted, pr_unweighted = load_pageranks(TEST_SHARE, num_repos, DAMPING_FACTOR)

    if pr_weighted is None or pr_unweighted is None:
        # [C] Compute PageRank
        pr_weighted = compute_pagerank(G_weighted, DAMPING_FACTOR)
        pr_unweighted = compute_pagerank(G_unweighted, DAMPING_FACTOR)
        # Cache them
        save_pageranks(pr_weighted, pr_unweighted, TEST_SHARE, num_repos, DAMPING_FACTOR)
    else:
        print("[C] Using cached PageRank vectors – skipping computation.")

    # Show top developers
    top_devs = sorted(pr_weighted.items(), key=lambda x: x[1], reverse=True)[:10]
    print("\nTop 10 developers by weighted PageRank:")
    for dev, score in top_devs:
        print(f"  {dev}: {score:.8f}")

    # Select random seed developers (reproducible due to fixed random seed)
    all_devs = list(G_weighted.nodes())
    valid_seeds = []
    all_devs = list(G_weighted.nodes())
    random.shuffle(all_devs)  # random order
    for dev in all_devs:
        if len(valid_seeds) >= EVALUATION_SAMPLE_SIZE:
            break
        recs = recommend_developers(G_weighted, pr_weighted, dev, k=1)
        if recs:
            valid_seeds.append(dev)

    seed_developers = valid_seeds
    print(f"\nSelected {len(seed_developers)} random seed developers for evaluation: {seed_developers}")

    # [E] Evaluation output – create recommendation survey CSV
    eval_df = evaluate(
        G_weighted, pr_weighted, pr_unweighted, G_unweighted, seed_developers
    )
    eval_df.to_csv("recommendation_survey.csv", index=False)
    print("\n[E] Recommendation survey saved to recommendation_survey.csv")

    elapsed_time = time.time() - begin_time
    elapsed_minutes = round(elapsed_time / 60, 2)

    print(f"\nElapsed time: {elapsed_minutes} minutes for {TEST_SHARE * 100}% of repos")


if __name__ == "__main__":
    main()