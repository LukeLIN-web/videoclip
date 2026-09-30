#!/bin/bash
# grade.sh — one film look for real photos + AI video.  Output: 1920x804, 24 fps.
#
# usage: grade.sh [options] INPUT OUTPUT
#   -y OFFSET   vertical crop position when cutting 16:9 (or taller) to 2.39:1.
#               -1 = keep top, 0 = centre (default), 1 = keep bottom. Any value in between.
#   -x OFFSET   same, horizontal (for sources wider than 2.39:1). default 0
#   -d SECONDS  duration for still-image input (default 5). Ignored for video.
#   -g GRAIN    grain strength 0..1 (default 0.5)
#   -h HALATION halation opacity 0..1 (default 0.28)
#   -s SAT      saturation (default 0.94)
#   -c CODEC    prores (default: ProRes 422 HQ, yuv422p10le) | h264 (libx264 CRF 12, yuv420p, for previews)
#   -a          drop audio (default: keep first audio stream as 48 kHz PCM if present)
#
# Chain (all grading at 16-bit RGB):
#   cover-scale (lanczos) -> crop 1920x804 at offset -> 24 fps -> curves (gently lifted blacks, soft
#   shoulder) -> colorbalance (teal-blue shadows, amber highlights; pl=0 because pl=1 posterises clipped highlights) -> saturation
#   -> halation (highlights isolated, blurred, tinted red-orange, screened back) -> vignette (multiply
#   with 16-bit mask) -> 35mm grain (animated, gaussian-softened, overlay-blended so it is luma-weighted:
#   strongest in mid-tones, falling off toward black & white) -> ProRes 422 HQ, bt709 tagged.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
YOFF=0; XOFF=0; DUR=5; GRAIN=0.5; HAL=0.28; SAT=0.94; CODEC=prores; AUDIO=1
while getopts "y:x:d:g:h:s:c:a" o; do
  case $o in y) YOFF=$OPTARG;; x) XOFF=$OPTARG;; d) DUR=$OPTARG;; g) GRAIN=$OPTARG;; h) HAL=$OPTARG;;
             s) SAT=$OPTARG;; c) CODEC=$OPTARG;; a) AUDIO=0;; *) sed -n '2,20p' "$0"; exit 1;; esac
done
shift $((OPTIND-1))
[ $# -eq 2 ] || { sed -n '2,20p' "$0"; exit 1; }
IN="$1"; OUT="$2"
VIG="$HERE/vignette_1920x804.png"
[ -f "$VIG" ] || python3 "$HERE/make_vignette.py" >/dev/null

# still image?
LOW=$(printf "%s" "$IN" | tr "[:upper:]" "[:lower:]")
case "$LOW" in *.jpg|*.jpeg|*.png|*.tif|*.tiff|*.heic|*.webp) STILL=1;; *) STILL=0;; esac
if [ $STILL -eq 1 ]; then INOPT=(-loop 1 -framerate 24 -t "$DUR" -i "$IN"); AUDIO=0
else INOPT=(-i "$IN"); fi
HAS_A=0
if [ $AUDIO -eq 1 ] && ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 "$IN" | grep -q .; then HAS_A=1; fi

# untagged HD video (e.g. Veo mp4) is Rec.709 by convention; ffmpeg would otherwise assume BT.601
IM=auto
if [ $STILL -eq 0 ]; then
  CS=$(ffprobe -v error -select_streams v:0 -show_entries stream=color_space -of csv=p=0 "$IN" | head -1)
  case "$CS" in ""|unknown|reserved) IM=bt709;; esac
fi

GA=$(python3 -c "print(round(0.10+0.55*$GRAIN,3))")      # overlay opacity of the grain plate
GN=$(python3 -c "print(int(18+30*$GRAIN))")               # noise amplitude on the plate
# saturation as a 16-bit-safe Rec.709 luma-preserving channel mix
SATMIX=$(python3 -c "
s=$SAT; L=(0.2126,0.7152,0.0722); n='rgb'
print(':'.join(f'{n[i]}{n[j]}={(L[j]*(1-s)+(s if i==j else 0)):.5f}' for i in range(3) for j in range(3)))")

FC="[0:v]scale=w=1920:h=804:force_original_aspect_ratio=increase:flags=lanczos+accurate_rnd+full_chroma_int:in_color_matrix=$IM,\
crop=1920:804:(iw-1920)*(0.5+($XOFF)/2):(ih-804)*(0.5+($YOFF)/2),fps=24,setsar=1,format=gbrp16le,\
curves=master='0/0.032 0.12/0.105 0.5/0.5 0.86/0.875 1/0.965',\
colorbalance=rs=-0.075:gs=-0.005:bs=0.065:rm=0.018:gm=0.004:bm=-0.02:rh=0.075:gh=0.028:bh=-0.075:pl=0,\
colorchannelmixer=$SATMIX,split=2[base][h];\
[h]curves=all='0/0 0.62/0 0.85/0.35 1/1',gblur=sigma=22:steps=3,colorchannelmixer=rr=1:gg=0.48:bb=0.22,format=gbrp16le[hal];\
[base][hal]blend=all_mode=screen:all_opacity=$HAL,format=gbrp16le[b1];\
[1:v]format=gbrp16le,scale=1920:804[vig];\
[b1][vig]blend=all_mode=multiply:shortest=1,format=gbrp16le[b2];\
color=c=0x808080:s=1920x804:r=24,format=gray,noise=alls=$GN:allf=t,gblur=sigma=0.65,format=gbrp16le[gr];\
[b2][gr]blend=all_mode=overlay:all_opacity=$GA:shortest=1,\
scale=out_color_matrix=bt709:out_range=tv,format=yuv422p10le[v]"

if [ "$CODEC" = "h264" ]; then
  VENC=(-c:v libx264 -preset slow -crf 12 -pix_fmt yuv420p -profile:v high -tune film)
  FC="${FC/format=yuv422p10le[v]/format=yuv420p[v]}"
else
  VENC=(-c:v prores_ks -profile:v 3 -vendor apl0 -pix_fmt yuv422p10le)
fi
AMAP=(); [ $HAS_A -eq 1 ] && AMAP=(-map 0:a:0 -c:a pcm_s24le -ar 48000)
ffmpeg -hide_banner -loglevel "${GRADE_LOGLEVEL:-error}" -y "${INOPT[@]}" -loop 1 -framerate 24 -i "$VIG" \
  -filter_complex "$FC" -map "[v]" ${AMAP[@]+"${AMAP[@]}"} "${VENC[@]}" \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -r 24 -shortest "$OUT"
echo "graded -> $OUT"
