"""Bivariate income-context / CBG-proximity figure, using reported destinations."""
import json
import os
from pathlib import Path
import sys
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/paper2-income-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.colors import ListedColormap
import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import Transformer

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'v138_revision'
sys.path.insert(0,str(BASE))
from analyze_revision import panel, SHAPES
from figures import save


def main():
    d=panel()
    d=d[~d.state_fips.isin(['02','15'])].copy()
    ctx=pd.read_csv(BASE/'private/block_group_context.csv',dtype={'GEOID':str}).set_index('GEOID')
    d['county_income']=d.GEOID.map(ctx.income)
    cut=json.loads((BASE/'analysis/context_manifest.json').read_text())['quartile_cutpoints']
    d['income_band']=np.select([d.county_income<=cut[0],d.county_income<=cut[2]],[0,1],default=2)
    d['distance_band']=np.select([d.drive_2024<=30,d.drive_2024<=60],[0,1],default=2)
    d['class']=d.distance_band*3+d.income_band
    valid=d.POPULATION.gt(0)&d.county_income.notna()
    d['class']=d['class'].astype(float)
    d.loc[~valid,'class']=np.nan
    b=gpd.read_parquet(BASE/'private/display_geometry.parquet').merge(d,on='GEOID',validate='one_to_one')
    assert len(b)==236879
    palette=['#E8E8E8','#B5D6CE','#4D9F91','#E4B0BA','#ACB4C4','#4F88A7','#C34B67','#91648A','#3C5488']
    rows=[]
    for band,g in d[valid].groupby('income_band'):
        rows.append({'income_band':['Lower','Middle','Higher'][int(band)],'population':int(g.POPULATION.sum()),
                     'coverage30_pct':100*np.average(g.drive_2024<=30,weights=g.POPULATION),
                     'beyond60_population':int(g.loc[g.drive_2024>60,'POPULATION'].sum()),
                     'block_groups':len(g),'counties':g.county_fips.nunique()})
    summary=pd.DataFrame(rows)
    summary.to_csv(HERE/'analysis/bivariate_map_summary.csv',index=False)
    byclass=d[valid].groupby(['income_band','distance_band']).POPULATION.sum().reset_index()
    byclass.to_csv(HERE/'analysis/bivariate_class_populations.csv',index=False)
    fig=plt.figure(figsize=(16,10.4))
    fig.text(.035,.963,'Income and proximity to AI-reporting hospitals',fontsize=24,fontweight='bold',color='#24323B')
    fig.text(.035,.927,'2024 reported destinations | Block-group proximity paired with county median household income',fontsize=12,color='#53616C')
    ax=fig.add_axes([.025,.275,.70,.60])
    b.plot(column='class',ax=ax,cmap=ListedColormap(palette),vmin=-.5,vmax=8.5,linewidth=0,rasterized=True,
           missing_kwds={'color':'#F7F7F7'})
    bounds=b.total_bounds
    ax.set_xlim(bounds[0]-40000,bounds[2]+40000);ax.set_ylim(bounds[1]-40000,bounds[3]+40000)
    ax.set_axis_off()
    trans=Transformer.from_crs(4326,5070,always_xy=True)
    regions=[('Appalachian detail',(-86.5,34,-77.5,39.8),[.755,.59,.22,.27]),
             ('Lower Mississippi detail',(-93.5,31,-88.5,36.5),[.755,.255,.22,.255])]
    for i,(label,(west,south,east,north),position) in enumerate(regions):
        xx,yy=trans.transform([west,west,east,east],[south,north,south,north])
        box=[min(xx),min(yy),max(xx),max(yy)]
        detail=b.cx[box[0]:box[2],box[1]:box[3]]
        zoom=fig.add_axes(position)
        detail.plot(column='class',ax=zoom,cmap=ListedColormap(palette),vmin=-.5,vmax=8.5,linewidth=0,rasterized=True,
                    missing_kwds={'color':'#F7F7F7'})
        zoom.set_xlim(box[0],box[2]);zoom.set_ylim(box[1],box[3]);zoom.set_axis_off()
        zoom.set_title(f'{i+1}  {label}',loc='left',fontsize=12,pad=8)
        ax.add_patch(Rectangle((box[0],box[1]),box[2]-box[0],box[3]-box[1],fill=False,edgecolor='#303840',linewidth=1.1))
        ax.text(box[0],box[3]+30000,str(i+1),fontsize=12,fontweight='bold',color='#24323B')
    # One two-dimensional legend explicitly identifies both geographical units.
    legend=fig.add_axes([.075,.088,.112,.142])
    legend.imshow(np.arange(9).reshape(3,3),cmap=ListedColormap(palette),vmin=-.5,vmax=8.5,origin='lower',interpolation='nearest')
    legend.set_xticks([0,1,2],['Lower','Middle','Higher'],fontsize=9)
    legend.set_yticks([0,1,2],['<=30','30-60','>60'],fontsize=9)
    legend.tick_params(length=0,pad=5)
    for spine in legend.spines.values():spine.set_visible(False)
    legend.set_xlabel('County income',fontsize=10,labelpad=6)
    legend.set_ylabel('Proxy travel time (minutes)',fontsize=9,labelpad=8)
    fig.text(.047,.251,'How to read the colors',fontsize=12,fontweight='bold',color='#24323B')
    poor=summary.set_index('income_band').loc['Lower']
    fig.text(.245,.223,f"{poor.beyond60_population/1e6:.1f} million",fontsize=28,fontweight='bold',color='#A83C58')
    fig.text(.245,.184,'residents of lower-income counties live in block groups',fontsize=11,color='#24323B')
    fig.text(.245,.162,'more than 60 proxy minutes from a reported AI destination.',fontsize=11,color='#24323B')
    fig.text(.245,.121,'Dark rose combines lower county income with longer proximity times.',fontsize=10,color='#53616C')
    fig.text(.245,.100,'This describes places, not individual income or a causal income effect.',fontsize=10,color='#53616C')
    fig.text(.035,.039,r"Income bands: <=\$49,512.50; \$49,512.50-\$64,417.50; >\$64,417.50. Fixed boundaries from the manuscript's nonmetropolitan county quartiles.",fontsize=9,color='#53616C')
    fig.text(.035,.020,'Contiguous US; observed reports only, not imputed AI status. One representative point per CBG. Pale background: zero population or missing income. Census geometry; AHA/CHR inputs.',fontsize=8.8,color='#53616C')
    save(fig,'income_access_bivariate_CBG')
    (HERE/'analysis/bivariate_map_verification.json').write_text(json.dumps({'mapped_block_groups':len(b),
        'income_is_county_level':True,'distance_is_CBG_representative_point':True,
        'total_map_population':int(d.POPULATION.sum()),'population_with_valid_income':int(d.loc[valid,'POPULATION'].sum()),
        'lower_income_beyond60_population':int(poor.beyond60_population),
        'income_thresholds':[cut[0],cut[2]],'distance_thresholds_minutes':[30,60],
        'regional_panels':'Illustrative fixed Appalachian and Lower Mississippi geographic windows; not statistically selected hotspots'},indent=2)+'\n')
    print(summary.to_string(index=False),flush=True)


if __name__=='__main__':main()
