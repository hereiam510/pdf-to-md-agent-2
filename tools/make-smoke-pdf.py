"""Create an explicitly synthetic source for local software verification."""
import sys
from pathlib import Path
import pymupdf

target = Path(sys.argv[1])
target.parent.mkdir(parents=True, exist_ok=True)
doc = pymupdf.open()
page = doc.new_page(width=595, height=842)
page.insert_text((60, 66), "FIELD NOTES", fontsize=11, color=(0.14, 0.48, 0.41))
page.insert_text((60, 108), "A small, complete section", fontsize=24)
page.insert_textbox((60, 145, 520, 250),
    "This document is a synthetic software fixture. It is not a source-quality benchmark.\n\n"
    "Preserve the quantity 25 mg and the negative: do not change the original wording. "
    "The second page belongs to the same requested section.", fontsize=12, lineheight=1.6)
page.draw_rect((60, 310, 530, 490), color=(0.1, 0.4, 0.35), fill=(0.91, 0.96, 0.93))
page.insert_text((84, 350), "SOURCE FIGURE", fontsize=13, color=(0.12, 0.4, 0.33))
page.draw_circle((145, 420), 30, color=(0.18, 0.5, 0.4), fill=(0.3, 0.62, 0.5))
page.draw_line((185, 420), (330, 420), color=(0.18, 0.5, 0.4), width=2)
page.insert_text((345, 425), "Keep this relationship", fontsize=12)
page.insert_text((60, 525), "Figure 1. An unchanged source region.", fontsize=11)
page.insert_text((292, 790), "1", fontsize=10)
page = doc.new_page(width=595, height=842)
page.insert_text((60, 80), "The section continues", fontsize=22)
page.insert_textbox((60, 120, 520, 250), "This is the complete final paragraph.\n\n"
                    "A saved version can be reopened and exported without another model request.\n\n"
                    "End of the synthetic section.", fontsize=12, lineheight=1.6)
page.insert_text((292, 790), "2", fontsize=10)
doc.save(target)
doc.close()
