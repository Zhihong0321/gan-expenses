"""Attach Taobao purchase details and the corresponding checkout amounts."""
from io import BytesIO
from pathlib import Path

from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "claim-aug16-to-oct08"
OUTPUT = ROOT / "output/pdf/Aug-Oct-2026_Expense-Claim_with-Taobao-receipts.pdf"
RECORDS = [
    (7, "2026-09-07", "Alibaba Cloud / GLM API - order 1", "56.20", "5127724153479072920", "2026-09_Taobao_Order_MYR56.20.png", "Spending Snapshot, page 4"),
    (8, "2026-09-08", "Alibaba Cloud / GLM API - order 2", "56.23", "5127225051654018546", "2026-09_Taobao_Order_MYR56.23.png", "Spending Snapshot, page 5"),
    (13, "2026-09-25", "Gemini AI Pro subscription", "10.57", "5127741612108018546", "2026-09-25_mPay_FPX_CNY16.80_RM10.57.jpg", "mPay / revPAY FPX screenshot"),
    (14, "2026-09-25", "GLM / Qwen multi-model API plan", "25.38", "5127476582174164121", "2026-09_Taobao_Order_MYR25.38.png", "Spending Snapshot, page 6"),
    (17, "2026-10-01", "Tavily Search API keys", "5.09", "5127804325197036910", "2026-09_Taobao_Order_MYR5.09.png", "Spending Snapshot, page 7"),
]


def build():
    report = PdfReader(ROOT / "Aug-Oct-2026_Expense-Claim.pdf")
    writer = PdfWriter()
    writer.append(report)
    writer.add_outline_item("Expense claim report - RM 2,757.71", 0)
    width, height = landscape(A4)
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(width, height))
    details = PdfReader(ROOT / "Spending Snapshot Detail.pdf")
    # Keep each successful order as a separate crop, with its date and status.
    crops = {7: (9, 0.0, 0.267), 8: (10, 0.766, 1.0),
             13: (11, 0.430, 0.625), 14: (11, 0.233, 0.430),
             17: (11, 0.0, 0.233)}
    crop_dir = BATCH / "taobao-receipts"
    crop_dir.mkdir(exist_ok=True)
    for index, (row, date, title, amount, order, filename, source) in enumerate(RECORDS, 1):
        pdf.setFillColor(HexColor("#17243b"))
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(36, height - 43, "TAOBAO SUPPORTING PURCHASE RECORD")
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(36, height - 65, f"Claim entry #{row}: {title}")
        pdf.drawRightString(width - 36, height - 65, f"RM {amount}")
        pdf.setFont("Helvetica", 9)
        pdf.drawString(36, height - 83, f"Claim date: {date}   |   Order reference in claim: {order}")
        pdf.setFillColor(HexColor("#526178"))
        source_page, top, bottom = crops[row]
        pdf.drawString(36, height - 99, f"Purchase record: Spending Snapshot Detail, page {source_page} | Transaction successful")
        source_image = details.pages[source_page - 1].images[0]
        with Image.open(BytesIO(source_image.data)) as original:
            cropped = original.crop((0, round(original.height * top), original.width, round(original.height * bottom)))
            cropped.save(crop_dir / f"purchase-{order}.png")
            iw, ih = cropped.size
            scale = min((width - 72) / iw, 155 / ih)
            w, h = iw * scale, ih * scale
            pdf.drawImage(ImageReader(cropped), (width - w) / 2, height - 115 - h, width=w, height=h)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(36, 300, f"Matching checkout amount: RM {amount}")
        with Image.open(BATCH / filename) as image:
            iw, ih = image.size
            scale = min((width - 72) / iw, 250 / ih)
            w, h = iw * scale, ih * scale
            pdf.drawImage(ImageReader(image), (width - w) / 2, 40 + (250 - h) / 2, width=w, height=h)
        pdf.setFont("Helvetica", 8)
        pdf.drawString(36, 20, f"Claim entry #{row} | Order {order} | RM {amount}")
        pdf.drawRightString(width - 36, 20, f"Receipt {index} of 5")
        pdf.showPage()
    pdf.save()
    buffer.seek(0)
    writer.append(PdfReader(buffer))
    for index, (row, _, title, amount, *_) in enumerate(RECORDS):
        writer.add_outline_item(f"Entry {row}: {title} - RM {amount}", len(report.pages) + index)
    writer.add_metadata({"/Title": "Aug-Oct 2026 Expense Claim with Taobao Supporting Records", "/Author": "Gan Zhi Hong"})
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("wb") as file:
        writer.write(file)
    result = PdfReader(OUTPUT)
    assert len(result.pages) == len(report.pages) + 5
    for index, record in enumerate(RECORDS):
        page = result.pages[len(report.pages) + index]
        assert record[3] in page.extract_text()
        assert record[4] in page.extract_text()
        assert len(page.images) == 2
    # The portal opens the same per-purchase evidence shown in the submission.
    import pypdfium2 as pdfium
    rendered = pdfium.PdfDocument(str(OUTPUT))
    for index, record in enumerate(RECORDS):
        image = rendered[len(report.pages) + index].render(scale=2).to_pil()
        image.save(crop_dir / f"receipt-{record[4]}.png")
    print(f"Created {OUTPUT} ({len(result.pages)} pages)")


if __name__ == "__main__":
    build()
