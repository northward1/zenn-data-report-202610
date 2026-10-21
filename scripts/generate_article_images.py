import sqlite3
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

def format_monthly_labels(month_list, sparse=False):
    """
    横軸フォーマット:
    1行目に月番号 (01, 02, 03...) が整然と並び、
    年の切り替わり（01月または先頭）のみ2行目に年 (2024, 2025, 2026) を表示: '01\n2024'
    sparse=True の場合は偶数月を空文字にして間引き（サブプロット等の狭い領域用）
    """
    labels = []
    for i, m in enumerate(month_list):
        y, mo = m.split('-')
        if mo == '01' or i == 0:
            labels.append(f"{mo}\n{y}")
        elif sparse and int(mo) % 2 == 0:
            labels.append("")
        else:
            labels.append(mo)
    return labels

# ==========================================
# 1. 記事数の推移 (images/articles_trend.png)
# ==========================================
query1 = """
SELECT 
    substr(published_at, 1, 7) as month,
    COUNT(*) as total_count
FROM articles
WHERE status = 'success' AND published_at >= '2024-01-01' AND published_at <= '2026-10-21'
GROUP BY month
ORDER BY month ASC;
"""
df1 = pd.read_sql_query(query1, conn)

fig, ax = plt.subplots(figsize=(11, 4.8))
x = range(len(df1['month']))
bars = ax.bar(x, df1['total_count'], color='#4C72B0', alpha=0.9, width=0.65)

ax.set_xticks(x)
ax.set_xticklabels(format_monthly_labels(df1['month']), rotation=0, fontsize=8.5)
ax.set_ylabel('月間記事投稿本数 (本)', fontsize=11, fontweight='bold')

# ピーク時と直近の値を注記
for i, tot in enumerate(df1['total_count']):
    if df1['month'][i] in ['2024-12', '2025-12', '2026-06', '2026-09']:
        ax.text(i, tot + 150, f"{tot:,}", ha='center', fontsize=8.5, fontweight='bold', color='#333333')

plt.tight_layout()
plt.savefig('images/articles_trend.png', dpi=300)
plt.close()
print("1. images/articles_trend.png generated.")

# ==========================================
# 2. Like数・ブックマーク数の推移 (images/likes_and_bookmarks_trend.png)
# ==========================================
query2 = """
SELECT 
    substr(published_at, 1, 7) as month,
    COUNT(*) as total_articles,
    SUM(liked_count) as total_likes,
    SUM(bookmarked_count) as total_bookmarks,
    ROUND(AVG(liked_count), 2) as avg_likes,
    ROUND(AVG(bookmarked_count), 2) as avg_bookmarks
FROM articles
WHERE status = 'success' AND published_at >= '2024-01-01' AND published_at <= '2026-10-21'
GROUP BY month
ORDER BY month ASC;
"""
df2 = pd.read_sql_query(query2, conn)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.8))
x = range(len(df2['month']))

# 左右サブプロットの横軸（狭いため偶数月を間引き、01月は年を併記）
tick_labels2 = format_monthly_labels(df2['month'], sparse=True)

# 左: 月間合計獲得数
ax1.plot(x, df2['total_likes'], color='#4C72B0', marker='o', linewidth=2.2, label='合計Like数')
ax1.plot(x, df2['total_bookmarks'], color='#8172B3', marker='^', linewidth=2.2, label='合計ブックマーク数')
ax1.set_xticks(x)
ax1.set_xticklabels(tick_labels2, rotation=0, fontsize=8.5)
ax1.set_ylabel('月間総獲得数 (件)', fontsize=10.5, fontweight='bold')
ax1.yaxis.set_major_formatter(plt.matplotlib.ticker.FuncFormatter(lambda val, pos: f"{int(val):,}"))
ax1.legend(loc='upper right', frameon=True, framealpha=0.9, fontsize=9.5)

# 右: 1記事あたり平均獲得数
ax2.plot(x, df2['avg_likes'], color='#4C72B0', marker='o', linewidth=2.2, label='平均Like数')
ax2.plot(x, df2['avg_bookmarks'], color='#8172B3', marker='^', linewidth=2.2, label='平均ブックマーク数')
ax2.set_xticks(x)
ax2.set_xticklabels(tick_labels2, rotation=0, fontsize=8.5)
ax2.set_ylabel('1記事あたり平均獲得数', fontsize=10.5, fontweight='bold')
ax2.legend(loc='upper right', frameon=True, framealpha=0.9, fontsize=9.5)

plt.tight_layout()
plt.savefig('images/likes_and_bookmarks_trend.png', dpi=300)
plt.close()
print("2. images/likes_and_bookmarks_trend.png generated.")

# ==========================================
# 3. 非ログインLikeの推移 (images/anonymous_likes_daily.png)
# ==========================================
query3 = """
SELECT 
    substr(published_at, 1, 10) as pub_date,
    SUM(authenticated_liked_count) as auth_likes,
    SUM(anonymous_liked_count) as anon_likes,
    SUM(liked_count) as total_likes,
    ROUND(SUM(anonymous_liked_count) * 100.0 / NULLIF(SUM(liked_count), 0), 1) as anon_pct
FROM articles
WHERE status = 'success' AND published_at >= '2026-08-01' AND published_at <= '2026-10-19'
GROUP BY pub_date
ORDER BY pub_date ASC;
"""
df3 = pd.read_sql_query(query3, conn)

fig, ax1 = plt.subplots(figsize=(12, 5))
ax2 = ax1.twinx()

x = range(len(df3['pub_date']))
# 棒グラフ (全体シェア 81.8% と 18.2% を凡例に明記)
b1 = ax1.bar(x, df3['auth_likes'], label='ログインLike (81.8%)', color='#4C72B0', alpha=0.85, width=0.65)
b2 = ax1.bar(x, df3['anon_likes'], bottom=df3['auth_likes'], label='非ログインLike (18.2%)', color='#55A868', alpha=0.85, width=0.65)

# 折れ線 (日別比率)
line = ax2.plot(x, df3['anon_pct'], color='#E28F42', marker='o', linewidth=2.2, markersize=4, label='日別 非ログインLike比率 (%)')

# 8/17 リリース日の縦線
release_idx = df3['pub_date'].tolist().index('2026-08-17')
ax1.axvline(x=release_idx - 0.5, color='#C44E52', linestyle='--', linewidth=1.8, label='8/17 機能リリース')

# 8/17以降の平均非ログインLike率 18.2% の基準線 (右軸)
ax2.axhline(y=18.2, xmin=release_idx / len(x), xmax=1.0, color='#E28F42', linestyle=':', linewidth=2, label='平均基準線 (18.2%)')

# 日付フォーマット関数 (YYYY-MM-DD -> M/D)
def format_daily_label(date_str):
    parts = date_str.split('-')
    m = int(parts[1])
    d = int(parts[2])
    return f"{m}/{d}"

# 軸設定 (5日おき + リリース日 + 最終日)
# リリース日 8/17 と近接する 8/16 (index 15) は重なり防止のため除外
raw_indices = [i for i in x if i % 5 == 0 or i == len(x)-1 or i == release_idx]
tick_indices = [i for i in raw_indices if i == release_idx or abs(i - release_idx) > 1]
tick_indices = sorted(list(set(tick_indices)))

ax1.set_xticks(tick_indices)
ax1.set_xticklabels([format_daily_label(df3['pub_date'][i]) for i in tick_indices], rotation=0, fontsize=8.5)

ax1.set_ylabel('日別獲得Like数', fontsize=11, fontweight='bold', color='#333333')
ax2.set_ylabel('非ログインLike比率 (%)', fontsize=11, fontweight='bold', color='#E28F42')
ax2.set_ylim(0, 35)
ax2.grid(False)

# 凡例統合
h1, l1 = ax1.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, loc='upper right', frameon=True, framealpha=0.9, fontsize=9.5)

plt.tight_layout()
plt.savefig('images/anonymous_likes_daily.png', dpi=300)
plt.close()
print("3. images/anonymous_likes_daily.png generated.")

# ==========================================
# 4. ストック記事の非ログインLike獲得比率（当月=100とした指数）(images/longtail_stock_likes.png)
# ==========================================
query4 = """
SELECT 
    CASE 
        WHEN published_at >= '2026-09-01' THEN 0
        WHEN published_at >= '2026-08-17' THEN 1
        WHEN published_at >= '2026-08-01' THEN 2
        WHEN published_at >= '2026-07-01' THEN 3
        WHEN published_at >= '2026-04-01' THEN 4
        WHEN published_at >= '2026-01-01' THEN 5
        WHEN published_at >= '2025-01-01' THEN 6
        WHEN published_at >= '2024-01-01' THEN 7
        ELSE 8
    END as grp_id,
    AVG(anonymous_liked_count) as avg_anon,
    COUNT(*) as count
FROM articles
WHERE status = 'success' AND published_at >= '2021-01-01' AND published_at <= '2026-09-30'
GROUP BY grp_id
ORDER BY grp_id ASC;
"""
df4 = pd.read_sql_query(query4, conn)
base_val = df4[df4['grp_id'] == 0]['avg_anon'].values[0]
df4['index_100'] = (df4['avg_anon'] / base_val) * 100

labels = [
    "当月\n(09月)",
    "8月後半\n(導入後)",
    "8月前半\n(導入前)",
    "2ヶ月前\n(07月)",
    "3〜6ヶ月前",
    "半年〜1年前",
    "1年前\n(2025)",
    "2年前\n(2024)",
    "3年以上前"
]

fig, ax = plt.subplots(figsize=(10.5, 4.8))
x = range(len(labels))

# 導入後（初動あり）はオレンジ系、導入前（ストックのみ）は青系で色分け
colors = ['#DD8452', '#DD8452', '#4C72B0', '#4C72B0', '#4C72B0', '#4C72B0', '#4C72B0', '#4C72B0', '#4C72B0']
bars = ax.bar(x, df4['index_100'], color=colors, width=0.55, alpha=0.88)

ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=8.5, fontweight='bold')
ax.set_ylabel('非ログインLike獲得比 (当月 = 100)', fontsize=10.5, fontweight='bold')
ax.set_ylim(0, 115)

# バーの上に比率数値を表記（実測値として小数点第2位まで表示）
for bar in bars:
    yval = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2, yval + 1.5, f"{yval:.2f}", ha='center', fontsize=8.5, fontweight='bold')

plt.tight_layout()
plt.savefig('images/longtail_stock_likes.png', dpi=300)
plt.close()
print("4. images/longtail_stock_likes.png generated.")

# ==========================================
# 5. 推定月間獲得ログインLike数推移 (images/estimated_likes_trend.png)
# ==========================================
query5 = """
SELECT 
    substr(published_at, 1, 7) as pub_month,
    COUNT(*) as article_count,
    SUM(authenticated_liked_count) as cohort_total_likes
FROM articles
WHERE status = 'success' AND published_at >= '2021-01-01' AND published_at <= '2026-10-21'
GROUP BY pub_month
ORDER BY pub_month ASC;
"""
df_cohort = pd.read_sql_query(query5, conn)
all_months = df_cohort['pub_month'].tolist()

# 記事本文の推定比率に基づく未正規化ウェイト（当月 = 100）
# 翌月: 11.2, 翌々月: 5.9, 3〜12ヶ月後: 4.3, それ以降: 2.5
raw_weights = {0: 100.0, 1: 11.2, 2: 5.9}
for m in range(3, 13):
    raw_weights[m] = 4.3
for m in range(13, 37):
    raw_weights[m] = 2.5

monthly_likes = {m: {'flow': 0.0, 'stock': 0.0, 'total': 0.0} for m in all_months}

for idx, row in df_cohort.iterrows():
    p_m = row['pub_month']
    p_likes = row['cohort_total_likes']
    p_idx = all_months.index(p_m)
    
    # 各コホートがクロール時点までに経過した有効な lag のみで重みを正規化
    # （直近月のLikeが未来に切り捨てられて過小評価されるバイアスを防止）
    valid_lags = [lag for lag in raw_weights if p_idx + lag < len(all_months)]
    total_w = sum(raw_weights[lag] for lag in valid_lags)
    
    for lag in valid_lags:
        w_norm = raw_weights[lag] / total_w
        t_m = all_months[p_idx + lag]
        if lag == 0:
            monthly_likes[t_m]['flow'] += p_likes * w_norm
        else:
            monthly_likes[t_m]['stock'] += p_likes * w_norm
        monthly_likes[t_m]['total'] += p_likes * w_norm

display_months = [m for m in all_months if '2024-01' <= m <= '2026-09']

# ==========================================
# 5. 推定月間獲得ログインLike数推移 (images/estimated_likes_trend.png)
# ==========================================
flow_likes = [monthly_likes[m]['flow'] for m in display_months]
stock_likes = [monthly_likes[m]['stock'] for m in display_months]
total_likes = [monthly_likes[m]['total'] for m in display_months]

fig, ax1 = plt.subplots(figsize=(11.5, 4.8))
x = range(len(display_months))

b1 = ax1.bar(x, flow_likes, label='その月に投稿された記事', color='#DD8452', alpha=0.85, width=0.6)
b2 = ax1.bar(x, stock_likes, bottom=flow_likes, label='以前に投稿された記事', color='#4C72B0', alpha=0.85, width=0.6)

ax1.set_xticks(x)
ax1.set_xticklabels(format_monthly_labels(display_months), rotation=0, fontsize=8.5)
ax1.set_ylabel('推定プラットフォーム月間獲得ログインLike数 (件/月)', fontsize=11, fontweight='bold', color='#333333')
ax1.yaxis.set_major_formatter(plt.matplotlib.ticker.FuncFormatter(lambda val, pos: f"{int(val):,}"))
ax1.set_ylim(0, max(total_likes) * 1.12)
ax1.legend([b2, b1], [b2.get_label(), b1.get_label()], loc='upper right', frameon=True, framealpha=0.9, fontsize=10)

for i, tot in enumerate(total_likes):
    ax1.text(i, tot + max(total_likes) * 0.015, f"{tot/1000:.1f}k", ha='center', fontsize=8, fontweight='bold', color='#333333')

plt.tight_layout()
plt.savefig('images/estimated_likes_trend.png', dpi=300)
plt.close()
print("5. images/estimated_likes_trend.png generated.")

# ==========================================
# 6. 推定月間総PV推移 (images/estimated_pv_trend.png)
# ログインLike 1件あたり 322.5 PV（ログイン100PV + 外部非ログイン222.5PV）で換算
# ==========================================
PV_PER_AUTH_LIKE = 322.5
flow_pv = [(monthly_likes[m]['flow'] * PV_PER_AUTH_LIKE) / 1_000_000 for m in display_months]
stock_pv = [(monthly_likes[m]['stock'] * PV_PER_AUTH_LIKE) / 1_000_000 for m in display_months]
total_pv = [(monthly_likes[m]['total'] * PV_PER_AUTH_LIKE) / 1_000_000 for m in display_months]

fig, ax1 = plt.subplots(figsize=(11.5, 4.8))

x = range(len(display_months))
b1 = ax1.bar(x, flow_pv, label='その月に投稿された記事', color='#DD8452', alpha=0.85, width=0.6)
b2 = ax1.bar(x, stock_pv, bottom=flow_pv, label='以前に投稿された記事', color='#4C72B0', alpha=0.85, width=0.6)

ax1.set_xticks(x)
ax1.set_xticklabels(format_monthly_labels(display_months), rotation=0, fontsize=8.5)
ax1.set_ylabel('推定プラットフォーム月間総PV (百万PV/月)', fontsize=11, fontweight='bold', color='#333333')
ax1.set_ylim(0, max(total_pv) * 1.12)

# 凡例（上が「以前に投稿された記事」、下が「その月に投稿された記事」）
ax1.legend([b2, b1], [b2.get_label(), b1.get_label()], loc='upper right', frameon=True, framealpha=0.9, fontsize=10)

for i, tot in enumerate(total_pv):
    ax1.text(i, tot + max(total_pv) * 0.015, f"{tot:.1f}M", ha='center', fontsize=8, fontweight='bold', color='#333333')

plt.tight_layout()
plt.savefig('images/estimated_pv_trend.png', dpi=300)
plt.close()
print("6. images/estimated_pv_trend.png generated.")

print("All article images generated successfully in images/!")

