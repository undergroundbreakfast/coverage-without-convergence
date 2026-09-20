"""Larger relative typography for the supplementary print-size figures."""
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent

def main():
    source=(HERE/'maturity_map.py').read_text()
    source=source.replace('figsize=(16.6, 11.2)','figsize=(11, 7.6)')
    source=source.replace('fontsize=9,','fontsize=11,').replace('fontsize=9)','fontsize=11)')
    source=source.replace('fontsize=10.5','fontsize=11').replace('labelsize=9','labelsize=11')
    source=source.replace('[.176, .087, .129, .191]','[.176, .087, .20, .191]')
    source=source.replace('origin="lower", interpolation="nearest"','origin="lower", interpolation="nearest", aspect="auto"')
    source=source.replace('[.77, .323, .218, .274]','[.77, .315, .218, .255]')
    source=source.replace('Expanding only*','Expanding only').replace('Neither reported*','Neither reported')
    source=source.replace('["Metro\\n1-3", "Nonmetro\\n4-6", "Nonmetro\\n7-9"]','["1-3", "4-6", "7-9"]')
    source=source.replace('County rurality (RUCC)','County RUCC (1-3 = metro)')
    source=source.replace('Reported implementation within 30 proxy minutes','Reported stage within 30 proxy minutes')
    source=source.replace('d  Residents by proximity category','d  Residents by proximity category')
    source=re.sub(r'    fig.text\(\.035, \.020,[\s\S]*?    output = HERE / "figures"',
                  '    output = HERE.parent / "v143_revision/figures"',source)
    source=source.replace('AI_maturity_rurality_proximity_2024.{ext}','Supplementary_Figure_5_v143.{ext}')
    exec(compile(source,str(HERE/'maturity_map.py'),'exec'),{'__file__':str(HERE/'maturity_map.py'),'__name__':'__main__'})


if __name__ == "__main__":
    main()
