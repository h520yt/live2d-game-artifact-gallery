"""Build the two default-pose shoe plates from their independent outline curves.

Usage: python build_default_shell.py OUTPUT_DIR {shell,structure,final}
Requires NumPy and Pillow for offline asset preparation.
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

if len(sys.argv) != 3 or sys.argv[2] not in {"shell", "structure", "final"}:
    raise SystemExit(__doc__)

repo = Path(__file__).resolve().parents[2]
source = repo / "azur_lane/config/outfits/baifeng_3"
dest = Path(sys.argv[1])
stage = sys.argv[2]
cfg = json.loads((source / "outfit_01.json").read_text(encoding="utf8"))
with Image.open(source / cfg["atlas"]) as image:
    base = image.convert("RGBA")
atlas = base.copy()
cfg["atlas"] = "outfit_01_shell.png"

# Each list runs from the back of the shoe to the toe in that foot's own
# reference plate. The cap and side are two curves of the same projected shell.
parts={
 "ArtMesh13":{
  "lip":[(41,105),(45,111),(57,118),(80,123),(107,128),(130,135),(149,143),(165,146),(174,141)],
  "far":[(40,98),(46,103),(58,110),(79,116),(101,120),(128,126),(147,133),(166,137)],
  "top":[(160,143),(165,137),(179,132),(199,130),(220,129),(240,130),(261,135),(283,143),(303,153),(322,165),(338,178),(348,190)],
  "join":[(155,147),(169,153),(187,165),(211,177),(234,185),(260,190),(287,189),(312,184),(334,177),(348,190)],
  "welt":[(39,154),(46,159),(61,162),(85,164),(108,169),(129,179),(154,192),(181,203),(212,212),(242,218),(273,220),(303,217),(325,210),(341,200),(348,190)],
  "waist":[(40,167),(57,173),(83,175),(105,181),(128,190),(152,204),(179,216),(213,226),(245,232),(273,233),(300,229),(325,221),(342,209),(350,198),(348,190)],
  "tongue":[(135,137),(138,124),(145,113),(155,106),(169,102),(181,98),(193,100),(201,105),(208,117),(215,130),(222,133),(213,148),(197,151),(177,150),(159,148)],
  "rear":[(39,104),(40,120),(39,139),(39,154)],"side_top":(174,141),
  "heel":[(41,164),(39,173),(42,181),(56,184),(76,184),(100,184),(107,178),(92,169),(68,166)],
  "strap":[(150,132),(158,124),(169,122),(184,130),(201,143),(218,151),(214,161),(204,169),(190,165),(174,153),(159,144)],
  "metalDx":0,"metalDy":1,
 },
 "ArtMesh18":{
  "lip":[(59,91),(64,102),(74,113),(93,125),(113,136),(133,143),(151,147),(165,145),(176,138),(183,128)],
  "far":[(62,74),(68,75),(79,79),(96,85),(120,94),(143,105),(162,114),(182,123)],
  "top":[(176,137),(185,128),(201,124),(219,126),(238,135),(253,146),(269,156),(288,169),(308,182),(319,194)],
  "join":[(177,139),(191,145),(205,155),(223,167),(240,178),(261,185),(282,188),(304,185),(319,194)],
  "welt":[(57,112),(64,133),(77,144),(105,148),(126,157),(148,168),(170,180),(195,194),(218,207),(241,215),(266,221),(288,221),(305,215),(316,207),(322,198),(319,194)],
  "waist":[(58,122),(65,144),(82,156),(108,159),(128,168),(150,181),(175,194),(198,206),(220,218),(243,226),(265,230),(287,230),(306,223),(319,215),(325,204),(322,198),(319,194)],
  "tongue":[(164,141),(169,123),(176,113),(185,109),(197,110),(209,117),(220,127),(231,133),(224,146),(210,153),(189,153),(172,149)],
  "rear":[(61,74),(57,84),(56,101),(57,112)],"side_top":(183,128),
  "heel":[(61,141),(66,153),(76,164),(93,166),(107,164),(116,157),(96,149),(78,143)],
  "strap":[(160,138),(166,127),(178,123),(190,127),(206,137),(223,143),(238,151),(234,159),(220,166),(204,160),(190,152),(172,145)],
  "metalDx":1,"metalDy":0,
 },
}

def stretch(points,closed=False):
    ring=np.array(points,dtype=float)
    seq=np.vstack((ring[-1] if closed else ring[0],ring,
        ring[0] if closed else ring[-1],ring[1] if closed else ring[-1]))
    out=[]
    for i in range(len(ring) if closed else len(ring)-1):
        a,b,c,d=seq[i:i+4]
        for t in np.linspace(0,1,13,endpoint=False):
            q=b+0.5*t*((c-a)+t*(2*a-5*b+4*c-d+t*(3*b-a-3*c+d)))
            out.append(tuple(q))
    out.append(tuple(ring[0] if closed else ring[-1]))
    return out

def shape(size,path,stroke=None):
    ss=4
    img=Image.new("L",(size[0]*ss,size[1]*ss))
    d=ImageDraw.Draw(img)
    seq=[(round(x*ss),round(y*ss)) for x,y in path]
    if stroke is None:
        d.polygon(seq,fill=255)
    else:
        d.line(seq,fill=255,width=round(stroke*ss),joint="curve")
    return np.array(img.resize(size,Image.Resampling.LANCZOS),dtype=float)/255

def band(size,path,top,bottom):
    pts=np.asarray(path)
    u=pts+[0,top]; l=pts+[0,bottom]
    return shape(size,[*u,*reversed(l)])

def fill(color,mask):
    if np.ndim(color)==1:
        color=np.broadcast_to(color,(*mask.shape,3))
    return Image.fromarray(np.uint8(np.rint(np.clip(np.dstack((color,mask)),0,1)*255)))

def rgb(hex_code):
    return [int(hex_code[i:i+2],16)/255 for i in (0,2,4)]

def masks(anchor,size,p):
    lip=stretch(p["lip"])
    far=stretch(p["far"])
    top=stretch(p["top"])
    join=stretch(p["join"])
    welt=stretch(p["welt"])
    waist=stretch(p["waist"])
    back=stretch(p["rear"])
    # The far/cavity surfaces sit behind the stocking. The near cap goes
    # over it and physically meets the tongue at the forward edge.
    far_shape=shape(size,[*far,(far[-1][0]-3,far[-1][1]+13),*reversed(lip),*back[:13]])
    far_cap=band(size,far,-.3,4.7)
    cavity=shape(size,[*(np.array(far)+[0,3.1]),*(np.array(lip)[::-1]+[0,3.3])])
    vamp=shape(size,[*top,*reversed(join),(top[0][0]-5,top[0][1]+9)])
    side=shape(size,[*lip,*join[10:],*reversed(welt),*reversed(back)])
    heel=shape(size,stretch(p["heel"],True))
    sole=shape(size,[*welt,*reversed(waist)])
    tongue=shape(size,stretch(p["tongue"],True))
    collar=band(size,lip,-2.1,4.6)
    # A narrower, independent surface inside the lip is available for the
    # contact shadow when materials are enabled.
    inner=band(size,lip,-3.6,-.4)
    strap=shape(size,stretch(p["strap"],True))
    if anchor=="ArtMesh18":
        x,y=np.meshgrid(np.arange(size[0])+.5,np.arange(size[1])+.5)
        cutoff=np.interp(x,[55,63,66,75,88],[92,87,80,74,72])
        back= np.clip((y-cutoff+.35)/1.4,0.,1.)
        far_shape*=back
        far_cap*=back
        cavity*=back
        side*=back
    return dict(far=far_shape,far_cap=far_cap,cavity=cavity,vamp=vamp,side=side,
                heel=heel,sole=sole,tongue=tongue,collar=collar,inner=inner,
                strap=strap,paths=[lip,far,top,join,welt,waist])

color={
  "far-quarter":"336e8d","cavity":"5441a7","heel":"376e69","midsole":"57b772",
  "near-quarter":"2e89bd","vamp":"63bce2","throat-wall":"ae76d5","collar":"e8be4b",
  "strap":"8b62c1","buckle":"d685a5","toe":"547a92",
}
def read_tiles(form):
    layers={}
    for layer in form["layers"]:
        x, y, w, h = layer["region"]
        layers[layer["id"]] = base.crop((x, y, x + w, y + h))
    return layers

def smooth(v):
    t=np.clip(v,0,1)
    return t*t*(3-2*t)

def curve_y(points,x):
    sorted_points=sorted(points)
    return np.interp(x,[p[0] for p in sorted_points],[p[1] for p in sorted_points])

def texture(image,x,y):
    """Premultiplied bilinear sampling from one existing material plate."""
    pixels=np.asarray(image,dtype=float)/255
    pixels[:,:,:3]*=pixels[:,:,3:]
    x=np.clip(x-.5,0,image.width-1)
    y=np.clip(y-.5,0,image.height-1)
    i,j=np.floor(x).astype(int),np.floor(y).astype(int)
    u,v=x-i,y-j
    result=np.zeros((*i.shape,4))
    for dx,dy,w in ((0,0,(1-u)*(1-v)),(1,0,u*(1-v)),(0,1,(1-u)*v),(1,1,u*v)):
        result+=pixels[np.minimum(j+dy,image.height-1),np.minimum(i+dx,image.width-1)]*w[:,:,None]
    result[:,:,:3]=np.divide(result[:,:,:3],result[:,:,3:],out=np.zeros_like(result[:,:,:3]),where=result[:,:,3:]>0)
    return result

def compose_original(tiles,ids):
    im=Image.new("RGBA",next(iter(tiles.values())).size)
    for id in ids:
        if id in tiles: im.alpha_composite(tiles[id])
    return im

def tint(value,kind):
    colors={
        "leather":[1.035,1.0,.982],
        "sole":[1.05,1.0,.956],
        "inside":[1.23,1.0,.84],
        "edge":[1.08,.99,.93],
    }
    return np.clip(value[:,:,None]*colors[kind],0,1)

def material(anchor,size,p,m,source):
    w,h=size
    x,y=np.meshgrid(np.arange(w)+.5,np.arange(h)+.5)
    lip,far,top,seam,welt,waist=m["paths"]
    upper_0=max(p["top"][0][0]-4,0)
    upper_1=p["top"][-1][0]
    width=upper_1-upper_0
    along=np.clip((x-upper_0)/width,0,1)
    crest=curve_y(top,x)
    seam_y=curve_y(seam,x)
    z=np.clip((y-crest)/np.maximum(seam_y-crest,6),0,1)
    height=curve_y(welt,x)
    lip_y=curve_y(lip,x)
    far_y=curve_y(far,x)
    front=anchor=="ArtMesh13"
    combined=compose_original(source,["near-quarter","vamp","toe","instep"])
    if front:
        source_top=[(166,122),(205,126),(233,131),(253,133),(273,141),(305,160),(347,187)]
        source_bottom=[(166,157),(205,174),(233,185),(260,190),(300,190),(347,198)]
    else:
        source_top=[(176,123),(202,129),(222,137),(241,143),(263,152),(284,170),(320,199)]
        source_bottom=[(176,149),(209,170),(240,186),(276,193),(300,203),(320,209)]
    src_top=curve_y(source_top,x)
    src_bottom=curve_y(source_bottom,x)
    sampled=texture(combined,x,src_top+(src_bottom-src_top)*z)
    native=sampled[:,:,:3]@[.23,.57,.20]
    # Each curve uses its own projected normal. The existing leather
    # supplies grain and irregular reflections inside that shape.
    crown=np.exp(-((z-(.39+.11*along))/.27)**2)*np.exp(-((along-.52)/.49)**2)
    highlight_a=np.exp(-((z-(.24+.43*along))/.105)**2)*np.exp(-((along-.57)/.42)**2)
    shadow=1-.38*smooth((z-.73)/.27)
    top_value=(.075+.145*crown+.066*highlight_a)*shadow
    top_value=top_value*.73+np.minimum(native,.46)*sampled[:,:,3]*.35
    upper_color=tint(top_value,"leather")
    near_crest=np.where(x<p["lip"][-1][0],lip_y,seam_y)
    depth=np.clip((y-near_crest)/np.maximum(height-near_crest,7),0,1)
    old_side=texture(combined,x,y+1)
    leather=old_side[:,:,:3]@[.25,.58,.17]
    roll=np.exp(-((depth-.34)/.29)**2)
    heel_spot=np.exp(-((x-(52 if front else 68))/14)**2)*np.exp(-((depth-.38)/.27)**2)
    nose_spot=np.exp(-((along-.87)/.12)**2)*np.exp(-((depth-.22)/.17)**2)
    shade=.044+.076*roll+.11*heel_spot+.077*nose_spot
    shade=shade*(1-.35*smooth((depth-.73)/.27))
    side_color=tint(shade*.77+np.minimum(leather,.63)*old_side[:,:,3]*.28,"leather")
    sole_depth=np.clip((y-height)/np.maximum(2,curve_y(waist,x)-height),0,1)
    old_sole=texture(source["midsole"],x,y)
    rubber=.030+.026*np.exp(-((sole_depth-.48)/.36)**2)+.027*np.exp(-((sole_depth-.18)/.11)**2)
    rubber+=np.minimum(old_sole[:,:,:3]@[.25,.55,.20],.19)*old_sole[:,:,3]*.27
    rubber*=1-.35*smooth((sole_depth-.66)/.34)
    sole_color=tint(rubber,"sole")
    heel_color=tint(.035+.032*np.exp(-((x-(47 if front else 70))/10)**2)+.013*np.sin(np.clip((y-147)/40,0,1)*np.pi),"sole")
    native_tongue=compose_original(source,["vamp","throat-wall","strap"])
    old_tongue=texture(native_tongue,x-1,y+2)
    grain=old_tongue[:,:,:3]@[.29,.52,.19]
    tongue_mid=np.exp(-((x-(162 if front else 187))/23)**2)*np.exp(-((y-(121 if front else 125))/12)**2)
    tongue_color=tint(.057+.10*tongue_mid+np.minimum(grain,.44)*old_tongue[:,:,3]*.39,"leather")
    old_strap=texture(source["strap"],x,y)
    strap_luma=old_strap[:,:,:3]@[.27,.53,.20]
    strap_color=tint(.075+.08*tongue_mid+np.minimum(strap_luma,.45)*old_strap[:,:,3]*.38,"leather")
    opening=np.clip((y-far_y)/np.maximum(lip_y-far_y,4),0,1)
    liner=tint(.071+.028*np.sin(opening*np.pi),"inside")
    far_wall=tint(.040+.025*np.sin(opening*np.pi)+.023*np.exp(-((opening-.20)/.13)**2),"inside")
    collar_dist=y-lip_y
    rim=tint(.064+.058*np.exp(-((collar_dist+.8)/.9)**2)+.042*np.exp(-((collar_dist-1.5)/1.2)**2),"edge")
    return {"far-quarter":far_wall,"cavity":liner,"heel":heel_color,"midsole":sole_color,
            "vamp":upper_color,"toe":upper_color,"near-quarter":side_color,
            "throat-wall":tongue_color,"collar":rim,"strap":strap_color}

def dash_layer(size,points,weight,spacing,phase=0):
    pts=np.asarray(points)
    gaps=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1))]
    marks=Image.new("L",(size[0]*4,size[1]*4)); d=ImageDraw.Draw(marks)
    for begin in np.arange(phase,gaps[-1]-2,spacing):
        indices=np.linspace(begin,min(begin+spacing*.46,gaps[-1]),3)
        x=np.interp(indices,gaps,pts[:,0]); y=np.interp(indices,gaps,pts[:,1])
        d.line([tuple(np.rint([a*4,b*4]).astype(int)) for a,b in zip(x,y)],fill=220,
               width=max(1,round(weight*4)))
    return np.array(marks.resize(size,Image.Resampling.LANCZOS),dtype=float)/255

def finish(tile,anchor,name,size,p,m):
    lip,far,top,seam,welt,waist=m["paths"]
    if name=="midsole":
        rolled=band(size,welt,.6,2.3)*m["sole"]
        tile.alpha_composite(fill(rgb("56443d"),rolled*.72))
        tile.alpha_composite(fill(rgb("0c0a0b"),band(size,welt,-.1,1.0)*m["sole"]*.85))
        tile.alpha_composite(fill(rgb("67544a"),dash_layer(size,np.array(welt)+[0,2.15],.64,4.3)*m["sole"]*.60))
    if name=="near-quarter":
        path=seam[7:-8]
        edge=band(size,path,-.25,1.5)*m["side"]
        tile.alpha_composite(fill(rgb("100d0e"),edge*.92))
        tile.alpha_composite(fill(rgb("887066"),dash_layer(size,np.array(path)+[0,1.45],.65,3.7)*m["side"]*.75))
        back=p["rear"][0][0]
        if anchor=="ArtMesh13":
            ankle=stretch([(back+4,113),(back+11,128),(back+17,144),(back+29,160)])
        else:
            ankle=stretch([(back+2,93),(back+10,111),(back+17,127),(back+25,142)])
        tile.alpha_composite(fill(rgb("141013"),shape(size,ankle,stroke=1.45)*m["side"]*.76))
        tile.alpha_composite(fill(rgb("584643"),dash_layer(size,np.array(ankle)+[1.3,0],.55,3.4)*m["side"]*.65))
    if name=="far-quarter":
        tile.alpha_composite(fill(rgb("634e44"),m["far_cap"]*.70))
        tile.alpha_composite(fill(rgb("170f0e"),band(size,far,2.5,4.4)*m["far_cap"]*.72))
    if name=="collar":
        tile.alpha_composite(fill(rgb("211512"),m["inner"]*.43))
        tile.alpha_composite(fill(rgb("91756a"),dash_layer(size,np.array(lip)+[0,3],.65,3.7)*m["collar"]*.67))
    if name=="throat-wall":
        crown=stretch(p["tongue"][:9])
        tile.alpha_composite(fill(rgb("765950"),shape(size,crown,stroke=.9)*m["tongue"]*.53))
    if name=="strap":
        seam=shape(size,stretch(p["strap"],True),stroke=1.4)*m["strap"]
        tile.alpha_composite(fill(rgb("2c2325"),seam*.72))
        tile.alpha_composite(fill(rgb("806761"),dash_layer(size,stretch(p["strap"],True),.85,3.45)*m["strap"]*.69))
    return tile

def main():
    for attachment in cfg["attachments"]:
        for form in attachment["forms"]:
            if form["anchor"] in parts:
                render_form(form)

    dest.mkdir(exist_ok=True, parents=True)
    definition = json.dumps(cfg, ensure_ascii=False, indent=2)
    definition = re.sub(r"\[(?:[ \t\n]*[^\s,\[\]{}]+,?)+[ \t\n]+\]",
                        lambda match: re.sub(r"\s+", " ", match.group()).replace("[ ", "[").replace(" ]", "]"),
                        definition)
    (dest / "outfit_01_shell.json").write_text(definition + "\n", encoding="utf8")
    atlas.save(dest / "outfit_01_shell.png", optimize=True)


def render_form(form):
    anchor = form["anchor"]
    front = anchor == "ArtMesh13"
    profile = parts[anchor]
    size = tuple(form["size"])
    original = read_tiles(form)
    surfaces = masks(anchor, size, profile)
    definitions = {layer["id"]: layer for layer in form["layers"]}
    if not front:
        definitions["cavity"] = definitions["lining-shadow"]
        definitions["throat-wall"] = definitions["instep"]

    # The far quarter and lining go below the stocking. The rest forms
    # the visible near side, with the welt and heel beneath the uppers.
    ordered = [
        ("far-quarter", surfaces["far"], True),
        ("cavity", surfaces["cavity"], True),
        ("heel", surfaces["heel"], False),
        ("midsole", surfaces["sole"], False),
        ("near-quarter", surfaces["side"], False),
        ("vamp", surfaces["vamp"], False),
        ("throat-wall", surfaces["tongue"], False),
        ("collar", surfaces["collar"], False),
    ]

    palette = color
    metallic = Image.new("RGBA", size)
    if stage == "shell":
        palette = {**color, "vamp": "438bb6", "throat-wall": "438bb6"}
    else:
        x, y = np.meshgrid(np.arange(size[0]) + .5, np.arange(size[1]) + .5)
        toe_seam = (276 if front else 261) + (y - (160 if front else 161)) * .21
        toe = np.clip((x - toe_seam + 1.45) / 2.9, 0, 1) * surfaces["vamp"]
        toe_pass = next(i + 1 for i, (name, _, _) in enumerate(ordered) if name == "vamp")
        ordered.insert(toe_pass, ("toe", toe, False))
        metallic.paste(original["buckle"], (profile["metalDx"], profile["metalDy"]))
        ordered.extend([
            ("strap", surfaces["strap"], False),
            ("buckle", np.asarray(metallic.getchannel("A")) / 255, False),
        ])

    colors = material(anchor, size, profile, surfaces, original) if stage == "final" else None
    new_layers = []
    for name, mask, behind in ordered:
        previous = definitions[name]
        region = previous["region"]
        layer = {"id": name, "region": region}
        for key in ("stiffness", "pivot"):
            if key in previous:
                layer[key] = previous[key]
        if behind:
            layer["behind"] = True
        if name == "collar":
            layer["after"] = "ArtMesh12" if front else "ArtMesh217"
        if colors is None:
            tile = fill(rgb(palette[name]), mask)
        elif name == "buckle":
            tile = metallic
        else:
            tile = finish(fill(colors[name], mask), anchor, name, size, profile, surfaces)
        atlas.paste(tile, tuple(region[:2]))
        new_layers.append(layer)
    form["layers"] = new_layers


if __name__ == "__main__":
    main()

