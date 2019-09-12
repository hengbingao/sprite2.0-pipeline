#%%
import pysam
from collections import defaultdict
import argparse


def parse_args():

    parser = argparse.ArgumentParser(description='Add tags to bam file')
    parser.add_argument('-i', '--input', dest='input_bams', nargs='+', type=str, required=True,
                        help='BAM(s) path(s) for which to consolidate the XS/XT tag')
    parser.add_argument('-o', '--out_bam', dest='output_bam', type=str, required=True,
                        help='Out BAM path')

    args = parser.parse_args()
    return args


#%%
def main():

    # bams = ["/mnt/data/RNA_DNA_SPRITE/featureCounts/PB49.RNAex.hisat2.mapq20.bam.featureCounts.bam", 
    # "/mnt/data/RNA_DNA_SPRITE/featureCounts/PB49.RNAr.hisat2.mapq20.bam.featureCounts.bam",
    # "/mnt/data/RNA_DNA_SPRITE/featureCounts/PB49.RNAin.hisat2.mapq20.bam.featureCounts.bam"]

    # bam = "/mnt/data/RNA_DNA_SPRITE/featureCounts/PB49.RNA.hisat2.mapq20.bam"

    # output_bam = "/mnt/data/RNA_DNA_SPRITE/featureCounts/PB49.RNA.hisat2.mapq20.anno.bam"

    opts = parse_args()

    anno_dict = get_annotation(opts.input_bams)
    anno_clean = clean_annotation(anno_dict)
    add_annotation(bam, opts.output_bam, anno_clean)




#%%
def get_annotation(bams):
    '''Read through bam files and extract featureCounts annotation for each read
    and combine intron, exon and repeat annotation

    Args:
        bams(list): A list of bam file paths

    '''
    read_annotation = defaultdict(set)

    for bam in bams:
        #get annotation type based on bam name
        if 'RNAex' in bam:
            anno_type='exon'
        elif 'RNAin' in bam:
            anno_type='intron'
        elif 'RNAr' in bam:
            anno_type='repeat'
        else:
            raise Exception('Could not determine annotation type from file name')
        try:
            with pysam.AlignmentFile(bam, 'rb') as f:
                for read in f.fetch(until_eof = True):
                    name = read.query_name
                    #get featureCounts annotation
                    if read.has_tag('XT'):
                        anno = read.get_tag('XT')
                        read_annotation[name].add(anno + '-' + anno_type)
                    #only XS flag present if no feature identified
                    elif read.has_tag('XS'):
                        anno = read.get_tag('XS')
                        read_annotation[name].add(anno + '-' + 'none')
                    else:
                        raise Exception('XS tag missing, was featureCounts run?')
                    
        except ValueError:
            print('BAM file provided is not a BAM or is empty!')

    return read_annotation





#%%
def add_annotation(bam, output_bam, anno_dict):
    '''Add read annotation to a singular bam file

    Args:
        bam(str): Input bam to which annotation will be added
        output_bam(str): Output of input bam with annotation
        anno_dict(dict): read (key) and annotation (value) dictionary
    '''
    count = 0
    skipped = 0
    with pysam.AlignmentFile(bam, "rb") as in_bam, \
    pysam.AlignmentFile(output_bam, "wb", template=in_bam) as out_bam:

        for read in in_bam.fetch(until_eof = True):
            count += 1
            name = read.query_name
            anno = anno_dict.get(name, 'none')
            try:
                read.tags += [('XS', ''.join(anno))] #should be a single value
                out_bam.write(read)
            except KeyError:
                skipped += 1
    
    print('Total reads:', count)
    print('Reads with an error not written out:', skipped)

#%%
def clean_annotation(anno_dict):
    '''For a read with annotation, remove Unassigned_NoFeatures and concatenate the rest
    '''
    anno_out = defaultdict(str)
    for k, v in anno_dict.items():
        if len(v) > 1:
            new_anno = []
            for i in v:
                if i.split(':')[-1] == 'none':
                    continue
                else:
                    new_anno.append(i)
            anno_out[k] = ';'.join(new_anno)
        else:
            anno_out[k] = v

    return anno_out

#%%
