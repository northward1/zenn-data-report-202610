import sqlite3
import json
from collections import defaultdict
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import japanize_matplotlib

# スタイル設定
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams['font.sans-serif'] = ['Noto Sans CJK JP', 'IPAexGothic', 'sans-serif']
plt.rcParams['axes.edgecolor'] = '#cccccc'
plt.rcParams['axes.linewidth'] = 0.8

DB_PATH = 'zenn_stats.db'
conn = sqlite3.connect(DB_PATH)

print("Starting chart generation...")

# ==========================================
# 図1: 月別記事投稿数と大量投稿（月10本以上）の推移
# ==========================================
query1 = """
WITH monthly_authors AS (
    SELECT 
        substr(published_at, 1, 7) as month,
        user_name_hash,
        COUNT(*) as cnt
    FROM articles
    WHERE status = 'success' AND published_at >= '2024-01-01' AND published_at <= '2026-10-21'
    GROUP BY month, user_name_hash
),
monthly_agg AS (
    SELECT 
        month,
        SUM(cnt) as total_articles,
        SUM(CASE WHEN cnt >= 10 THEN cnt ELSE 0 END) as articles_10plus,
        SUM(CASE WHEN cnt < 10 THEN cnt ELSE 0 END) as articles_normal
    FROM monthly_authors
    GROUP BY month
)
SELECT 
    month,
    total_articles,
    articles_10plus,
    articles_normal,
    ROUND(articles_10plus * 100.0 / total_articles, 2) as pct_10plus
FROM monthly_agg
ORDER BY month ASC;
"""
df1 = pd.read_sql_query(query1, conn)

fig, ax1 = plt.subplots(figsize=(12, 5.5))
ax2 = ax1.twinx()

months = df1['month'].tolist()
x = range(len(months))

bars1 = ax1.bar(x, df1['articles_normal'], label='通常投稿 (<10本/月)', color='#4C72B0', alpha=0.85)
bars2 = ax1.bar(x, df1['articles_10plus'], bottom=df1['articles_normal'], label='大量投稿 (>=10本/月)', color='#C44E52', alpha=0.85)

line = ax2.plot(x, df1['pct_10plus'], color='#E28F42', marker='o', linewidth=2.5, markersize=5, label='大量投稿比率 (%)')

ax1.set_xticks(x)
ax1.set_xticklabels(months, rotation=45, ha='right', fontsize=9)
ax1.set_ylabel('月間記事投稿本数', fontsize=11, fontweight='bold', color='#333333')
ax2.set_ylabel('大量投稿記事の割合 (%)', fontsize=11, fontweight='bold', color='#E28F42')
ax2.grid(False)

# 凡例統合
handles1, labels1 = ax1.get_legend_handles_labels()
handles2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(handles1 + handles2, labels1 + labels2, loc='upper left', frameon=True, framealpha=0.9)

plt.title('図1: 月別記事投稿数と大量投稿（月10本以上/人）の推移 (2024〜2026年10月)', fontsize=13, fontweight='bold', pad=15)
plt.tight_layout()
plt.savefig('figures/fig1_monthly_articles_and_slop.png', dpi=300)
plt.close()
print("Figure 1 generated.")

# ==========================================
# 図2: エンゲージメントの劣化（ゼロLike率・ゼロBookmark率）
# ==========================================
query2 = """
SELECT 
    substr(published_at, 1, 7) as month,
    COUNT(*) as total_articles,
    SUM(CASE WHEN liked_count = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as zero_like_pct,
    SUM(CASE WHEN bookmarked_count = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as zero_bm_pct,
    ROUND(AVG(liked_count), 2) as avg_likes
FROM articles
WHERE status = 'success' AND published_at >= '2024-01-01' AND published_at <= '2026-10-21'
GROUP BY month
ORDER BY month ASC;
"""
df2 = pd.read_sql_query(query2, conn)

fig, ax1 = plt.subplots(figsize=(12, 5.5))
ax2 = ax1.twinx()

x = range(len(df2['month']))
line1 = ax1.plot(x, df2['zero_like_pct'], color='#C44E52', marker='s', linewidth=2.5, label='Like 0 の記事割合 (%)')
line2 = ax1.plot(x, df2['zero_bm_pct'], color='#8172B3', marker='^', linewidth=2.5, label='ブックマーク 0 の記事割合 (%)')
line3 = ax2.plot(x, df2['avg_likes'], color='#55A868', marker='o', linewidth=2, linestyle='--', label='1記事あたり平均Like数')

ax1.set_xticks(x)
ax1.set_xticklabels(df2['month'], rotation=45, ha='right', fontsize=9)
ax1.set_ylabel('0件エンゲージメント割合 (%)', fontsize=11, fontweight='bold', color='#333333')
ax2.set_ylabel('平均Like数', fontsize=11, fontweight='bold', color='#55A868')
ax2.grid(False)

# 凡例統合
h1, l1 = ax1.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, loc='center left', frameon=True, framealpha=0.9)

plt.title('図2: 新規記事エンゲージメントの推移（ゼロLike率・ゼロBookmark率の上昇）', fontsize=13, fontweight='bold', pad=15)
plt.tight_layout()
plt.savefig('figures/fig2_engagement_decay.png', dpi=300)
plt.close()
print("Figure 2 generated.")

# ==========================================
# 図3: 大量投稿記事 vs 通常記事の品質比較（2026年6月ピーク時）
# ==========================================
query3 = """
WITH author_june AS (
    SELECT 
        user_name_hash,
        COUNT(*) as cnt
    FROM articles
    WHERE status = 'success' AND published_at >= '2026-06-01' AND published_at < '2026-07-01'
    GROUP BY user_name_hash
)
SELECT 
    CASE WHEN a.cnt >= 10 THEN '大量投稿者 (>=10本/月)' ELSE '通常投稿者 (<10本/月)' END as author_group,
    COUNT(*) as total_articles,
    ROUND(AVG(art.liked_count), 2) as avg_likes,
    ROUND(AVG(art.bookmarked_count), 2) as avg_bookmarks,
    ROUND(SUM(CASE WHEN art.liked_count = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as zero_like_pct
FROM articles art
JOIN author_june a ON art.user_name_hash = a.user_name_hash
WHERE art.status = 'success' AND art.published_at >= '2026-06-01' AND art.published_at < '2026-07-01'
GROUP BY author_group;
"""
df3 = pd.read_sql_query(query3, conn)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8))

# 指標1: 平均Like & 平均ブックマーク
bar_width = 0.35
indices = range(len(df3))
ax1.bar([i - bar_width/2 for i in indices], df3['avg_likes'], width=bar_width, label='平均Like数', color='#4C72B0')
ax1.bar([i + bar_width/2 for i in indices], df3['avg_bookmarks'], width=bar_width, label='平均Bookmark数', color='#8172B3')
ax1.set_xticks(indices)
ax1.set_xticklabels(df3['author_group'], fontsize=10, fontweight='bold')
ax1.set_ylabel('平均獲得数', fontsize=10, fontweight='bold')
ax1.set_title('平均Like・Bookmark獲得数', fontsize=11, fontweight='bold')
ax1.legend()

# 数値ラベル
for i in indices:
    ax1.text(i - bar_width/2, df3['avg_likes'][i] + 0.1, f"{df3['avg_likes'][i]:.2f}", ha='center', fontsize=9)
    ax1.text(i + bar_width/2, df3['avg_bookmarks'][i] + 0.1, f"{df3['avg_bookmarks'][i]:.2f}", ha='center', fontsize=9)

# 指標2: ゼロLike率
colors = ['#C44E52', '#55A868']
ax2.set_xticks(range(len(df3['author_group'])))
bars = ax2.bar(range(len(df3['author_group'])), df3['zero_like_pct'], color=colors, width=0.5, alpha=0.85)
ax2.set_ylabel('ゼロLike記事の割合 (%)', fontsize=10, fontweight='bold')
ax2.set_title('ゼロLike率（誰にもLikeされない記事）', fontsize=11, fontweight='bold')
ax2.set_xticklabels(df3['author_group'], fontsize=10, fontweight='bold')
for bar in bars:
    yval = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2, yval + 1, f"{yval:.1f}%", ha='center', fontsize=10, fontweight='bold')

plt.suptitle('図3: 2026年6月（投稿ピーク時）における大量投稿記事 vs 通常記事の品質比較', fontsize=12, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('figures/fig3_slop_vs_normal_comparison.png', dpi=300)
plt.close()
print("Figure 3 generated.")

# ==========================================
# 図4: 過去ストック記事の直近閲覧状況（Tech vs Idea、年度別）
# ==========================================
query4 = """
SELECT 
    substr(published_at, 1, 4) as pub_year,
    article_type,
    COUNT(*) as total_articles,
    SUM(anonymous_liked_count) as total_anon_likes,
    ROUND(AVG(anonymous_liked_count), 4) as avg_anon,
    ROUND(SUM(CASE WHEN anonymous_liked_count > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as active_pct
FROM articles
WHERE status = 'success' AND published_at >= '2021-01-01' AND published_at < '2026-01-01'
GROUP BY pub_year, article_type
ORDER BY pub_year ASC, article_type ASC;
"""
df4 = pd.read_sql_query(query4, conn)

years = sorted(df4['pub_year'].unique())
tech_vals = df4[df4['article_type'] == 'tech']['avg_anon'].tolist()
idea_vals = df4[df4['article_type'] == 'idea']['avg_anon'].tolist()

fig, ax = plt.subplots(figsize=(9, 5))
x = range(len(years))
w = 0.35

b1 = ax.bar([i - w/2 for i in x], tech_vals, width=w, label='Tech (技術記事)', color='#4C72B0')
b2 = ax.bar([i + w/2 for i in x], idea_vals, width=w, label='Idea (アイデア・体験談)', color='#DD8452')

ax.set_xticks(x)
ax.set_xticklabels([f"{y}年公開" for y in years], fontsize=10, fontweight='bold')
ax.set_ylabel('1記事あたり平均 匿名Like獲得数\n(2026年8〜10月の直近外部流入)', fontsize=10, fontweight='bold')
ax.legend(fontsize=10)

# ラベル
for i in x:
    ax.text(i - w/2, tech_vals[i] + 0.0015, f"{tech_vals[i]:.4f}", ha='center', fontsize=9)
    ax.text(i + w/2, idea_vals[i] + 0.0015, f"{idea_vals[i]:.4f}", ha='center', fontsize=9)

plt.title('図4: 過去記事（ストック）の直近2ヶ月における匿名Like獲得率（Tech vs Idea）', fontsize=12, fontweight='bold', pad=15)
plt.tight_layout()
plt.savefig('figures/fig4_longtail_tech_vs_idea.png', dpi=300)
plt.close()
print("Figure 4 generated.")

# ==========================================
# 図5: 過去記事のトピック別「直近の外部検索流入」格差（TOP 10 vs BOTTOM 10）
# ==========================================
cur = conn.cursor()
cur.execute("""
SELECT topics, anonymous_liked_count, liked_count
FROM articles
WHERE status = 'success' AND published_at >= '2021-01-01' AND published_at < '2025-01-01'
""")

topic_stats = defaultdict(lambda: {'count': 0, 'anon_likes': 0, 'active_anon': 0})
for raw_topics, anon, tot in cur.fetchall():
    if not raw_topics:
        continue
    try:
        t_list = json.loads(raw_topics)
    except:
        continue
    for t in t_list:
        t_clean = t.strip()
        topic_stats[t_clean]['count'] += 1
        topic_stats[t_clean]['anon_likes'] += anon
        if anon > 0:
            topic_stats[t_clean]['active_anon'] += 1

major_topics = [t for t, s in topic_stats.items() if s['count'] >= 500]
results = []
for t in major_topics:
    s = topic_stats[t]
    avg_anon = s['anon_likes'] / s['count']
    act_pct = s['active_anon'] * 100.0 / s['count']
    results.append({'topic': t, 'count': s['count'], 'avg_anon': avg_anon, 'active_pct': act_pct})

df_topics = pd.DataFrame(results)
top10 = df_topics.sort_values(by='avg_anon', ascending=False).head(8)
bottom10 = df_topics.sort_values(by='avg_anon', ascending=True).head(8)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

# TOP
sns.barplot(data=top10, y='topic', x='avg_anon', ax=ax1, hue='topic', palette='Blues_r', legend=False)
ax1.set_title('今も外部から検索・閲覧されているトピック (TOP 8)', fontsize=11, fontweight='bold')
ax1.set_xlabel('1記事あたり平均 匿名Like獲得数', fontsize=10, fontweight='bold')
ax1.set_ylabel('トピック', fontsize=10, fontweight='bold')
for i, v in enumerate(top10['avg_anon']):
    ax1.text(v + 0.001, i, f"{v:.4f}", va='center', fontsize=9)

# BOTTOM
sns.barplot(data=bottom10, y='topic', x='avg_anon', ax=ax2, hue='topic', palette='Reds_r', legend=False)
ax2.set_title('AI代替等で外部閲覧が激減したトピック (BOTTOM 8)', fontsize=11, fontweight='bold')
ax2.set_xlabel('1記事あたり平均 匿名Like獲得数', fontsize=10, fontweight='bold')
ax2.set_ylabel('', fontsize=10)
for i, v in enumerate(bottom10['avg_anon']):
    ax2.text(v + 0.0005, i, f"{v:.4f}", va='center', fontsize=9)

plt.suptitle('図5: 過去記事（2021〜2024年公開）のトピック別 直近外部アクセス獲得格差', fontsize=12, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('figures/fig5_topic_stock_survival.png', dpi=300)
plt.close()
print("Figure 5 generated.")

# ==========================================
# 図6: 真の月間総PV推計（新規記事フローPV ＋ 過去記事ストックPVの合算）
# ==========================================
query6 = """
SELECT 
    substr(published_at, 1, 7) as pub_month,
    COUNT(*) as article_count,
    SUM(liked_count) as cohort_total_likes
FROM articles
WHERE status = 'success' AND published_at >= '2021-01-01' AND published_at <= '2026-10-21'
GROUP BY pub_month
ORDER BY pub_month ASC;
"""
df_cohort = pd.read_sql_query(query6, conn)
all_months = df_cohort['pub_month'].tolist()

# 時間減衰モデル（Like発生ウェイト）
# 公開月: 65% (初動), 翌月: 10%, 2ヶ月後: 5%, 3-12ヶ月後: 毎月1.5% (計15%), 13-36ヶ月後: 毎月0.2% (計5%)
weights = {0: 0.65, 1: 0.10, 2: 0.05}
for m in range(3, 13):
    weights[m] = 0.015
for m in range(13, 37):
    weights[m] = 0.002

monthly_likes = {m: {'flow': 0.0, 'stock': 0.0, 'total': 0.0} for m in all_months}

for idx, row in df_cohort.iterrows():
    p_m = row['pub_month']
    p_likes = row['cohort_total_likes']
    p_idx = all_months.index(p_m)
    
    for lag, w in weights.items():
        target_idx = p_idx + lag
        if target_idx < len(all_months):
            t_m = all_months[target_idx]
            if lag == 0:
                monthly_likes[t_m]['flow'] += p_likes * w
            else:
                monthly_likes[t_m]['stock'] += p_likes * w
            monthly_likes[t_m]['total'] += p_likes * w

# 2024年1月〜2026年9月（9月までが確定月、10月は途中月）を表示
display_months = [m for m in all_months if '2024-01' <= m <= '2026-09']
flow_pv = [(monthly_likes[m]['flow'] * 250) / 1_000_000 for m in display_months]
stock_pv = [(monthly_likes[m]['stock'] * 250) / 1_000_000 for m in display_months]
total_pv = [(monthly_likes[m]['total'] * 250) / 1_000_000 for m in display_months]
stock_share = [(monthly_likes[m]['stock'] * 100.0 / monthly_likes[m]['total']) if monthly_likes[m]['total'] > 0 else 0 for m in display_months]

fig, ax1 = plt.subplots(figsize=(12, 5.8))
ax2 = ax1.twinx()

x = range(len(display_months))
b1 = ax1.bar(x, stock_pv, label='過去記事のストックPV (検索・回遊)', color='#4C72B0', alpha=0.85, width=0.6)
b2 = ax1.bar(x, flow_pv, bottom=stock_pv, label='当月新規記事のフローPV (新着・トレンド)', color='#DD8452', alpha=0.85, width=0.6)

line = ax2.plot(x, stock_share, color='#C44E52', marker='o', linewidth=2.5, markersize=5, label='ストックPV依存比率 (%)')

ax1.set_xticks(x)
ax1.set_xticklabels(display_months, rotation=45, ha='right', fontsize=9)
ax1.set_ylabel('推定プラットフォーム月間総PV (百万PV/月)', fontsize=11, fontweight='bold', color='#333333')
ax2.set_ylabel('ストックPV依存比率 (%)', fontsize=11, fontweight='bold', color='#C44E52')
ax2.set_ylim(15, 65)
ax2.grid(False)

# 凡例統合
h1, l1 = ax1.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, loc='upper left', frameon=True, framealpha=0.9)

# 棒グラフの上に総PVの数値を表記
for i, tot in enumerate(total_pv):
    ax1.text(i, tot + 0.25, f"{tot:.1f}M", ha='center', fontsize=8, fontweight='bold', color='#333333')

plt.title('図6: カレンダー月別 プラットフォーム総PV推計（ストックPV ＋ 新規フローPVの合算）', fontsize=13, fontweight='bold', pad=15)
plt.tight_layout()
plt.savefig('figures/fig6_estimated_pv_trend.png', dpi=300)
plt.close()
print("Figure 6 generated.")

print("All charts generated successfully!")
