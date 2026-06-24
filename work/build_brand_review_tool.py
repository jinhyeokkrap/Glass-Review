import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "outputs" / "eyewear_form_research_300"
OUT = ROOT / "outputs" / "eyewear_brand_review_tool"


def load_items():
    with (DATA_ROOT / "metadata.csv").open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    items = []
    for row in rows:
        items.append(
            {
                "id": f"{int(row['index']):03d}",
                "index": int(row["index"]),
                "brand": row["brand"],
                "model": row["model"],
                "form": row.get("form_note") or "optical frame",
                "image": "../eyewear_form_research_300/" + row["image_path"].replace("\\", "/"),
                "thumb": "../eyewear_form_research_300/" + row["thumb_path"].replace("\\", "/"),
                "source": row.get("page_url", ""),
            }
        )
    return items


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    items = load_items()
    brands = sorted({item["brand"] for item in items})
    data_json = json.dumps({"items": items, "brands": brands}, ensure_ascii=False)

    html = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Eyewear Brand Review Tool</title>
  <style>
    :root {{
      --bg: #f5f6f2;
      --panel: #ffffff;
      --ink: #171918;
      --muted: #666f65;
      --line: #d9ded5;
      --accent: #20251f;
      --mark: #b24631;
      --hold: #b38721;
      --ok: #2f6b55;
      font-family: Arial, "Noto Sans KR", sans-serif;
      color: var(--ink);
      background: var(--bg);
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; min-height: 100vh; overflow: auto; }}
    button, input, select, textarea {{ font: inherit; }}
    button {{
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      border-radius: 6px;
      min-height: 34px;
      padding: 0 10px;
      cursor: pointer;
      white-space: nowrap;
    }}
    button.active {{ background: var(--accent); border-color: var(--accent); color: #fff; }}
    .app {{
      display: grid;
      grid-template-columns: 240px minmax(420px, 1fr) 380px;
      height: 100vh;
      min-width: 1040px;
      width: max(100vw, 1040px);
    }}
    aside, .detail {{
      background: var(--panel);
      border-right: 1px solid var(--line);
      min-height: 0;
      display: flex;
      flex-direction: column;
    }}
    .detail {{ border-right: 0; border-left: 1px solid var(--line); }}
    .brand-head, .topbar, .detail-head {{
      min-height: 64px;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      gap: 10px;
      flex: 0 0 auto;
    }}
    .brand-head, .detail-head {{ flex-direction: column; align-items: stretch; justify-content: center; }}
    h1 {{ margin: 0; font-size: 17px; line-height: 1.2; }}
    .count {{ color: var(--muted); font-size: 12px; }}
    .brand-list {{ flex: 1 1 auto; min-height: 0; overflow: auto; padding: 10px; }}
    .brand-btn {{
      width: 100%;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
      align-items: center;
      margin-bottom: 6px;
      text-align: left;
    }}
    .brand-btn span:last-child {{ color: var(--muted); font-size: 12px; }}
    .brand-btn.active span:last-child {{ color: rgba(255,255,255,.78); }}
    main {{ min-width: 0; min-height: 0; display: flex; flex-direction: column; position: relative; }}
    .topbar {{ justify-content: space-between; align-items: flex-start; flex-wrap: wrap; position: relative; z-index: 3; background: var(--panel); }}
    .filters {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
    .topbar > .filters:last-child {{ justify-content: flex-end; }}
    .search {{ width: 240px; height: 34px; border: 1px solid var(--line); border-radius: 6px; padding: 0 10px; background: #fff; }}
    select {{ height: 34px; border: 1px solid var(--line); border-radius: 6px; padding: 0 8px; background: #fff; }}
    .grid {{
      flex: 1 1 auto;
      min-height: 0;
      overflow: auto;
      padding: 14px;
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
      gap: 12px;
      align-content: start;
    }}
    .card {{
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      min-height: 222px;
      position: relative;
    }}
    .card.selected {{ outline: 3px solid var(--accent); }}
    .card[data-verdict="pick"] {{ border-color: var(--ok); }}
    .card[data-verdict="hold"] {{ border-color: var(--hold); }}
    .card[data-verdict="reject"] {{ opacity: .52; }}
    .card img {{
      width: 100%;
      aspect-ratio: 1.35 / 1;
      object-fit: contain;
      background: #fafbf9;
      border-bottom: 1px solid #e5e9e2;
      display: block;
    }}
    .card-body {{ padding: 9px 10px 10px; }}
    .meta-line {{ display: flex; justify-content: space-between; gap: 8px; color: var(--muted); font-size: 11px; }}
    .model {{ margin: 5px 0 0; font-size: 13px; line-height: 1.32; min-height: 34px; }}
    .rating {{ margin-top: 7px; color: #8c6b13; font-size: 12px; letter-spacing: 0; }}
    .badge {{
      position: absolute;
      top: 8px;
      right: 8px;
      min-width: 26px;
      height: 24px;
      border-radius: 6px;
      background: rgba(255,255,255,.92);
      border: 1px solid var(--line);
      display: grid;
      place-items: center;
      font-size: 12px;
    }}
    .detail-body {{ flex: 1 1 auto; min-height: 0; overflow: auto; padding: 16px; position: relative; z-index: 2; background: var(--panel); }}
    .hero {{
      width: 100%;
      aspect-ratio: 1.25 / 1;
      object-fit: contain;
      background: #fafbf9;
      border: 1px solid var(--line);
      border-radius: 8px;
      display: block;
      cursor: zoom-in;
    }}
    .detail-title {{ margin-top: 14px; }}
    .detail-title h2 {{ margin: 4px 0 4px; font-size: 20px; line-height: 1.2; }}
    .detail-title p {{ margin: 0; color: var(--muted); font-size: 13px; }}
    .review-block {{ margin-top: 16px; display: grid; gap: 10px; }}
    .seg {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }}
    .seg .pick.active {{ background: var(--ok); border-color: var(--ok); }}
    .seg .hold.active {{ background: var(--hold); border-color: var(--hold); }}
    .seg .reject.active {{ background: var(--mark); border-color: var(--mark); }}
    .score-row {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; }}
    .tag-row {{ display: flex; gap: 6px; flex-wrap: wrap; }}
    .tag.active {{ background: #33423a; border-color: #33423a; color: #fff; }}
    textarea {{
      width: 100%;
      min-height: 92px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      resize: vertical;
      line-height: 1.45;
    }}
    .detail-actions {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
    .source {{ color: #245b7a; font-size: 12px; word-break: break-all; }}
    .empty {{ padding: 40px; color: var(--muted); }}
    .modal {{
      position: fixed;
      inset: 0;
      z-index: 20;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 28px;
      background: rgba(18, 20, 18, .78);
    }}
    .modal.open {{ display: flex; }}
    .modal-panel {{
      width: min(1180px, 96vw);
      max-height: 94vh;
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      gap: 10px;
    }}
    .modal-head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      color: #fff;
    }}
    .modal-title {{
      min-width: 0;
      line-height: 1.25;
      font-size: 14px;
    }}
    .modal-title strong {{
      display: block;
      font-size: 18px;
    }}
    .modal-close {{
      border-color: rgba(255,255,255,.38);
      background: rgba(255,255,255,.12);
      color: #fff;
    }}
    .modal-img {{
      width: 100%;
      max-height: calc(94vh - 56px);
      object-fit: contain;
      background: #fafbf9;
      border-radius: 8px;
      display: block;
    }}
    @media (max-width: 1040px) {{
      .app {{ width: 1040px; }}
    }}
  </style>
</head>
<body>
  <div class="app">
    <aside>
      <div class="brand-head">
        <h1>Brand Review</h1>
        <div class="count" id="summary">{len(items)} frames</div>
      </div>
      <div class="brand-list" id="brandList"></div>
    </aside>
    <main>
      <div class="topbar">
        <div class="filters">
          <input class="search" id="search" placeholder="모델 / 브랜드 검색">
          <select id="verdictFilter">
            <option value="all">전체 상태</option>
            <option value="unreviewed">미리뷰</option>
            <option value="pick">Pick</option>
            <option value="hold">Hold</option>
            <option value="reject">Reject</option>
          </select>
          <select id="sortMode">
            <option value="index">수집 순서</option>
            <option value="rating">점수 높은 순</option>
            <option value="brand">브랜드/모델순</option>
          </select>
        </div>
        <div class="filters">
          <button id="exportCsv">CSV Export</button>
          <button id="exportJson">JSON Export</button>
          <button id="exportPicked">Picked JSON</button>
          <button id="savePickedFolder">Save Picks by Brand</button>
          <button id="clearFilter">Clear</button>
        </div>
      </div>
      <section class="grid" id="grid"></section>
    </main>
    <section class="detail">
      <div class="detail-head">
        <h1 id="detailBrand">Select Frame</h1>
        <div class="count" id="detailIndex">브랜드별로 훑고, 점수와 코멘트를 남기세요.</div>
      </div>
      <div class="detail-body" id="detail"></div>
    </section>
  </div>
  <div class="modal" id="imageModal" aria-hidden="true">
    <div class="modal-panel">
      <div class="modal-head">
        <div class="modal-title" id="modalTitle"></div>
        <button class="modal-close" id="modalClose">Close</button>
      </div>
      <img class="modal-img" id="modalImage" alt="">
    </div>
  </div>
  <script>
    const DATA = {data_json};
    const STORE_KEY = "eyewear-brand-review-v1";
    const tags = ["AI 글래스 적합", "두꺼운 템플", "얇은 림", "메탈", "아세테이트", "라운드", "스퀘어", "브릿지 참고", "노즈/착용감", "개성 강함"];
    let state = JSON.parse(localStorage.getItem(STORE_KEY) || "{{}}");
    let activeBrand = "All";
    let selectedId = DATA.items[0]?.id;

    function save() {{
      localStorage.setItem(STORE_KEY, JSON.stringify(state));
    }}
    function reviewOf(id) {{
      if (!state[id]) state[id] = {{ verdict: "", rating: 0, tags: [], note: "" }};
      return state[id];
    }}
    function brandCounts() {{
      const counts = {{ All: DATA.items.length }};
      DATA.items.forEach(item => counts[item.brand] = (counts[item.brand] || 0) + 1);
      return counts;
    }}
    function renderBrands() {{
      const list = document.getElementById("brandList");
      const counts = brandCounts();
      const brands = ["All", ...DATA.brands];
      list.innerHTML = brands.map(brand => `
        <button class="brand-btn ${{brand === activeBrand ? "active" : ""}}" data-brand="${{brand}}">
          <span>${{brand}}</span><span>${{counts[brand] || 0}}</span>
        </button>`).join("");
      list.querySelectorAll("button").forEach(btn => btn.onclick = () => {{
        activeBrand = btn.dataset.brand;
        render();
      }});
    }}
    function filteredItems() {{
      const q = document.getElementById("search").value.trim().toLowerCase();
      const verdict = document.getElementById("verdictFilter").value;
      const sort = document.getElementById("sortMode").value;
      let items = DATA.items.filter(item => {{
        const r = reviewOf(item.id);
        const brandOk = activeBrand === "All" || item.brand === activeBrand;
        const textOk = !q || `${{item.brand}} ${{item.model}} ${{item.form}}`.toLowerCase().includes(q);
        const verdictOk = verdict === "all" || (verdict === "unreviewed" ? !r.verdict : r.verdict === verdict);
        return brandOk && textOk && verdictOk;
      }});
      if (sort === "rating") items.sort((a, b) => reviewOf(b.id).rating - reviewOf(a.id).rating || a.index - b.index);
      if (sort === "brand") items.sort((a, b) => (a.brand + a.model).localeCompare(b.brand + b.model));
      return items;
    }}
    function stars(n) {{
      return "●".repeat(Number(n || 0)) + "○".repeat(5 - Number(n || 0));
    }}
    function renderGrid() {{
      const grid = document.getElementById("grid");
      const items = filteredItems();
      document.getElementById("summary").textContent = `${{items.length}} / ${{DATA.items.length}} frames`;
      if (!items.length) {{
        grid.innerHTML = `<div class="empty">조건에 맞는 프레임이 없습니다.</div>`;
        return;
      }}
      grid.innerHTML = items.map(item => {{
        const r = reviewOf(item.id);
        const label = r.verdict ? r.verdict[0].toUpperCase() : "";
        return `
          <article class="card ${{item.id === selectedId ? "selected" : ""}}" data-id="${{item.id}}" data-verdict="${{r.verdict}}">
            <div class="badge">${{label}}</div>
            <img src="${{item.thumb}}" alt="${{item.brand}} ${{item.model}}">
            <div class="card-body">
              <div class="meta-line"><span>${{item.id}}</span><span>${{item.brand}}</span></div>
              <div class="model">${{item.model}}</div>
              <div class="rating">${{stars(r.rating)}}</div>
            </div>
          </article>`;
      }}).join("");
      grid.querySelectorAll(".card").forEach(card => card.onclick = () => {{
        selectedId = card.dataset.id;
        render();
      }});
    }}
    function setVerdict(id, verdict) {{
      const r = reviewOf(id);
      r.verdict = r.verdict === verdict ? "" : verdict;
      save();
      render();
    }}
    function setRating(id, rating) {{
      reviewOf(id).rating = Number(rating);
      save();
      render();
    }}
    function toggleTag(id, tag) {{
      const r = reviewOf(id);
      r.tags = r.tags || [];
      r.tags = r.tags.includes(tag) ? r.tags.filter(t => t !== tag) : [...r.tags, tag];
      save();
      render();
    }}
    function renderDetail() {{
      const item = DATA.items.find(x => x.id === selectedId) || DATA.items[0];
      if (!item) return;
      const r = reviewOf(item.id);
      document.getElementById("detailBrand").textContent = item.brand;
      document.getElementById("detailIndex").textContent = `${{item.id}} · ${{item.model}}`;
      document.getElementById("detail").innerHTML = `
        <img class="hero" id="heroImage" src="${{item.image}}" alt="${{item.brand}} ${{item.model}}" title="Click to enlarge">
        <div class="detail-title">
          <p>${{item.brand}}</p>
          <h2>${{item.model}}</h2>
          <p>${{item.form}}</p>
        </div>
        <div class="review-block">
          <div class="seg">
            <button class="pick ${{r.verdict === "pick" ? "active" : ""}}" data-verdict="pick">Pick</button>
            <button class="hold ${{r.verdict === "hold" ? "active" : ""}}" data-verdict="hold">Hold</button>
            <button class="reject ${{r.verdict === "reject" ? "active" : ""}}" data-verdict="reject">Reject</button>
          </div>
          <div class="score-row">
            ${{[1,2,3,4,5].map(n => `<button class="${{r.rating === n ? "active" : ""}}" data-rating="${{n}}">${{n}}</button>`).join("")}}
          </div>
          <div class="tag-row">
            ${{tags.map(tag => `<button class="tag ${{(r.tags || []).includes(tag) ? "active" : ""}}" data-tag="${{tag}}">${{tag}}</button>`).join("")}}
          </div>
          <textarea id="note" placeholder="폼, 브릿지, 템플, AI 글래스 적용성 메모">${{r.note || ""}}</textarea>
          <div class="detail-actions">
            <button id="prev">Prev</button>
            <button id="next">Next</button>
          </div>
          <a class="source" href="${{item.source}}" target="_blank" rel="noreferrer">source</a>
        </div>`;
      const detailEl = document.getElementById("detail");
      detailEl.querySelectorAll("[data-verdict]").forEach(btn => btn.onclick = () => setVerdict(item.id, btn.dataset.verdict));
      detailEl.querySelectorAll("[data-rating]").forEach(btn => btn.onclick = () => setRating(item.id, Number(btn.dataset.rating)));
      detailEl.querySelectorAll("[data-tag]").forEach(btn => btn.onclick = () => toggleTag(item.id, btn.dataset.tag));
      document.getElementById("note").oninput = e => {{
        reviewOf(item.id).note = e.target.value;
        save();
      }};
      document.getElementById("heroImage").onclick = () => openImageModal(item);
      document.getElementById("prev").onclick = () => step(-1);
      document.getElementById("next").onclick = () => step(1);
    }}
    function openImageModal(item) {{
      const modal = document.getElementById("imageModal");
      document.getElementById("modalTitle").innerHTML = `<strong>${{item.brand}}</strong>${{item.id}} · ${{item.model}}`;
      const img = document.getElementById("modalImage");
      img.src = item.image;
      img.alt = `${{item.brand}} ${{item.model}}`;
      modal.classList.add("open");
      modal.setAttribute("aria-hidden", "false");
    }}
    function closeImageModal() {{
      const modal = document.getElementById("imageModal");
      modal.classList.remove("open");
      modal.setAttribute("aria-hidden", "true");
      document.getElementById("modalImage").removeAttribute("src");
    }}
    function step(delta) {{
      const items = filteredItems();
      const idx = items.findIndex(x => x.id === selectedId);
      if (!items.length) return;
      const next = items[(idx + delta + items.length) % items.length];
      selectedId = next.id;
      render();
    }}
    function exportRows(format) {{
      const rows = DATA.items.map(item => ({{ ...item, ...reviewOf(item.id) }}));
      downloadRows(rows, format, format === "json" ? "eyewear_review_export.json" : "eyewear_review_export.csv");
    }}
    function pickedRows() {{
      return DATA.items
        .filter(item => reviewOf(item.id).verdict === "pick")
        .map(item => ({{ ...item, ...reviewOf(item.id) }}));
    }}
    function downloadRows(rows, format, filename) {{
      let blob;
      if (format === "json") {{
        blob = new Blob([JSON.stringify(rows, null, 2)], {{ type: "application/json" }});
      }} else {{
        const headers = ["id","brand","model","form","verdict","rating","tags","note","image","source"];
        const csv = [headers.join(","), ...rows.map(row => headers.map(h => `"${{String(Array.isArray(row[h]) ? row[h].join("|") : row[h] || "").replaceAll('"','""')}}"`).join(","))].join("\\n");
        blob = new Blob([csv], {{ type: "text/csv" }});
      }}
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      a.click();
    }}
    function exportPickedRows() {{
      const rows = pickedRows();
      if (!rows.length) {{
        alert("No picked frames yet.");
        return;
      }}
      downloadRows(rows, "json", "picked_eyewear_review_export.json");
    }}
    function sanitizeFileName(value) {{
      return String(value || "item").replace(/[<>:"/\\\\|?*]+/g, "_").replace(/\\s+/g, " ").trim().slice(0, 90) || "item";
    }}
    async function writeTextFile(directoryHandle, filename, text, type = "text/plain") {{
      const handle = await directoryHandle.getFileHandle(filename, {{ create: true }});
      const writable = await handle.createWritable();
      await writable.write(new Blob([text], {{ type }}));
      await writable.close();
    }}
    async function savePickedByBrand() {{
      const rows = pickedRows();
      if (!rows.length) {{
        alert("Pick 제품이 아직 없습니다.");
        return;
      }}
      if (!window.showDirectoryPicker) {{
        exportPickedRows();
        alert("이 브라우저는 폴더 직접 저장을 지원하지 않아 Pick JSON을 다운로드했습니다.");
        return;
      }}
      try {{
        const root = await window.showDirectoryPicker({{ mode: "readwrite" }});
        const pickedRoot = await root.getDirectoryHandle("picked_by_brand", {{ create: true }});
        const manifest = [["id","brand","model","rating","tags","note","file","source"]];
        for (const item of rows) {{
          const brandDir = await pickedRoot.getDirectoryHandle(sanitizeFileName(item.brand), {{ create: true }});
          const fileName = `${{item.id}}_${{sanitizeFileName(item.brand)}}_${{sanitizeFileName(item.model)}}.jpg`;
          const response = await fetch(item.image);
          if (!response.ok) throw new Error(`Image fetch failed: ${{item.id}}`);
          const blob = await response.blob();
          const fileHandle = await brandDir.getFileHandle(fileName, {{ create: true }});
          const writable = await fileHandle.createWritable();
          await writable.write(blob);
          await writable.close();
          manifest.push([
            item.id,
            item.brand,
            item.model,
            item.rating || "",
            (item.tags || []).join("|"),
            item.note || "",
            `picked_by_brand/${{sanitizeFileName(item.brand)}}/${{fileName}}`,
            item.source || ""
          ]);
        }}
        const csv = manifest.map(row => row.map(cell => `"${{String(cell).replaceAll('"','""')}}"`).join(",")).join("\\n");
        await writeTextFile(pickedRoot, "picked_manifest.csv", csv, "text/csv");
        await writeTextFile(pickedRoot, "picked_manifest.json", JSON.stringify(rows, null, 2), "application/json");
        alert(`${{rows.length}}개 Pick 제품을 브랜드별 폴더로 저장했습니다.`);
      }} catch (error) {{
        console.error(error);
        exportPickedRows();
        alert("폴더 저장이 취소되었거나 실패해서 Pick JSON을 다운로드했습니다.");
      }}
    }}
    function render() {{
      renderBrands();
      renderGrid();
      renderDetail();
    }}
    document.getElementById("search").oninput = render;
    document.getElementById("verdictFilter").onchange = render;
    document.getElementById("sortMode").onchange = render;
    document.getElementById("clearFilter").onclick = () => {{
      activeBrand = "All";
      document.getElementById("search").value = "";
      document.getElementById("verdictFilter").value = "all";
      document.getElementById("sortMode").value = "index";
      render();
    }};
    document.getElementById("exportCsv").onclick = () => exportRows("csv");
    document.getElementById("exportJson").onclick = () => exportRows("json");
    document.getElementById("exportPicked").onclick = exportPickedRows;
    document.getElementById("savePickedFolder").onclick = savePickedByBrand;
    document.getElementById("modalClose").onclick = closeImageModal;
    document.getElementById("imageModal").onclick = e => {{
      if (e.target.id === "imageModal") closeImageModal();
    }};
    document.addEventListener("keydown", e => {{
      if (e.target.tagName === "TEXTAREA" || e.target.tagName === "INPUT") return;
      if (e.key === "Escape" && document.getElementById("imageModal").classList.contains("open")) {{
        closeImageModal();
        return;
      }}
      if (e.key === "ArrowRight") step(1);
      if (e.key === "ArrowLeft") step(-1);
      if (["1","2","3","4","5"].includes(e.key)) setRating(selectedId, Number(e.key));
      if (e.key.toLowerCase() === "p") setVerdict(selectedId, "pick");
      if (e.key.toLowerCase() === "h") setVerdict(selectedId, "hold");
      if (e.key.toLowerCase() === "r") setVerdict(selectedId, "reject");
    }});
    render();
  </script>
</body>
</html>
"""
    (OUT / "index.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
