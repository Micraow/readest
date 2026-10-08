#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <time.h>
#include "koptreflow.h"

static double now(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t); return t.tv_sec+t.tv_nsec/1e9; }

int main(int argc, char **argv) {
    if (argc != 4) { fprintf(stderr,"usage: harness input.ppm output.ppm metrics.json\n"); return 2; }
    FILE *f=fopen(argv[1],"rb"); if (!f) {perror(argv[1]);return 3;}
    char magic[3]; int width,height,maxval;
    if (fscanf(f,"%2s%d%d%d",magic,&width,&height,&maxval)!=4 || strcmp(magic,"P6") || maxval!=255) return 4;
    fgetc(f);
    KOPTContext c; memset(&c,0,sizeof(c));
    c.trim=0; c.wrap=1; c.white_threshold=255; c.paint_white_threshold=0;
    c.indent=1; c.columns=2; c.dev_dpi=144; c.dev_width=390; c.dev_height=844;
    c.page_width=390; c.page_height=844; c.justification=0;
    c.read_max_width=6000; c.read_max_height=6000;
    c.zoom=4.0; c.margin=0.04; c.quality=2.0; c.contrast=1.0;
    c.defect_size=0.0; c.line_spacing=1.2; c.word_spacing=-1.0; c.shrink_factor=0.9;
    c.bbox.x1=width/4.0; c.bbox.y1=height/4.0;
    bmp_init(&c.src); bmp_init(&c.dst); wrectmaps_init(&c.rectmaps);
    c.src.width=width; c.src.height=height; c.src.bpp=24; bmp_alloc(&c.src);
    for(int y=0;y<height;y++) if(fread(bmp_rowptr_from_top(&c.src,y),3,width,f)!=(size_t)width) return 5;
    fclose(f);
    double t=now(); k2pdfopt_reflow_bmp(&c); double elapsed=now()-t;
    struct rusage ru; getrusage(RUSAGE_SELF,&ru);
    f=fopen(argv[2],"wb"); if(!f)return 6;
    fprintf(f,"P6\n%d %d\n255\n",c.dst.width,c.dst.height);
    for(int y=0;y<c.dst.height;y++) fwrite(bmp_rowptr_from_top(&c.dst,y),3,c.dst.width,f);
    fclose(f);
    f=fopen(argv[3],"w"); if(!f)return 7;
    fprintf(f,"{\"engine_seconds\":%.9f,\"max_rss_kib\":%ld,\"source_size\":[%d,%d],\"output_size\":[%d,%d],\"map_count\":%d,\"maps\":[\n",elapsed,ru.ru_maxrss,width,height,c.dst.width,c.dst.height,c.rectmaps.n);
    for(int i=0;i<c.rectmaps.n;i++) {
        WRECTMAP *r=&c.rectmaps.wrectmap[i];
        fprintf(f,"%s{\"index\":%d,\"raw_coords\":[[%.9f,%.9f],[%.9f,%.9f],[%.9f,%.9f]],\"src_dpi\":[%.9f,%.9f],\"src_size\":[%d,%d],\"rotation\":%d,\"source_xywh\":[%.9f,%.9f,%.9f,%.9f],\"target_xywh\":[%.9f,%.9f,%.9f,%.9f]}",i?",\n":"",i,r->coords[0].x,r->coords[0].y,r->coords[1].x,r->coords[1].y,r->coords[2].x,r->coords[2].y,r->srcdpiw,r->srcdpih,r->srcwidth,r->srcheight,r->srcrot,r->coords[0].x*288/r->srcdpiw,r->coords[0].y*288/r->srcdpih,r->coords[2].x*288/r->srcdpiw,r->coords[2].y*288/r->srcdpih,r->coords[1].x,r->coords[1].y,r->coords[2].x,r->coords[2].y);
    }
    fprintf(f,"\n]}\n"); fclose(f);
    fprintf(stdout,"%d x %d => %d x %d; %d maps; %.4fs; %ld KiB RSS\n",width,height,c.dst.width,c.dst.height,c.rectmaps.n,elapsed,ru.ru_maxrss);
    bmp_free(&c.dst); wrectmaps_free(&c.rectmaps);
    if(c.rboxa)boxaDestroy(&c.rboxa); if(c.nboxa)boxaDestroy(&c.nboxa);
    if(c.rnai)numaDestroy(&c.rnai); if(c.nnai)numaDestroy(&c.nnai);
    return 0;
}
