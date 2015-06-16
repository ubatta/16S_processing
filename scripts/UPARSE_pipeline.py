#!/usr/bin/python

import os, sys, getopt, glob, subprocess, shutil

############################################################
# Run the UPARSE pipeline on demultiplexed, overlapped, 
# fasta files. 
#
# Full path to "quality_filtered" directory from demux_samples.py
# Requires UPARSE gold database, greengenes fasta, greengenes taxonomy in 
# "../database". These are relatively large databases (GG especially)
# email mbontrager@gmail.com if you need the databases.
#
# Usage: Run from script directory:
# UPARSE_pipeline.py - path/to/fasta/dir
#
# Author: Martin Bontrager
############################################################

def main():
    path = ''
    
    try:
        opts, args = getopt.getopt(sys.argv[1:],'hp:',['path='])
    except getopt.GetoptError:
        print('UPARSE_pipeline.py - path/to/fasta/dir')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('UPARSE_pipeline.py - path/to/fasta/dir')
            sys.exit()
        elif opt in ('-p', '--path'):
            path = arg
    
    os.chdir(path)
    sample_list = glob.glob('*.fasta')
    add_name_to_header(sample_list)
    run('mkdir fixed_headers')
    run('mv *.fa fixed_headers')

    # Pool samples into one large file
    os.chdir('fixed_headers')
    outfilename = 'concatenated.fa'
    with open(outfilename, 'wb') as outfile:
        for filename in glob.glob('*.fa'):
            if filename == outfilename:
                continue
            with open(filename, 'rb') as readfile:
                shutil.copyfileobj(readfile, outfile)
    run('mv ' + outfilename + ' ..')
    os.chdir('..')
    run('rm -r fixed_headers/')
    
    # Screen for short/long sequences:
    cmd = ('mothur135 \"#screen.seqs(fasta=concatenated.fa,' + 
           ' minlength=390, maxlength=450, processors=5)\"')
    run(cmd)
    run('rm concatenated.bad.accnos concatenated.fa')
    # Dereplicate sequences and sort by binned size
    run('usearch8 -derep_fulllength concatenated.good.fa -fastaout' + 
        ' uniques.fasta -sizeout -threads 5 -relabel BIN')
    run('usearch8 -sortbysize uniques.fasta -fastaout seqs_sorted.fasta ' +
        '-minsize 2')
    # Cluster into OTUs @ 97% ID
    run('usearch8 -cluster_otus seqs_sorted.fasta -otus otus.fa' + 
        ' -uparseout results.txt -relabel OTU_ -sizeout')
    # Filter out remaining chimeric reads and generate output table
    run('usearch8 -uchime_ref otus.fa -db ../database/uchime_gold.fa ' + 
        '-nonchimeras otu.uchime.fa -strand plus -threads 5')
    run('usearch8 -usearch_global concatenated.good.fa -db otu.uchime.fa ' + 
        '-strand plus -id 0.97 -uc readmap.uc -maxaccepts 8 -maxrejects 64 ' + 
        '-top_hit_only')
    run('rm uniques.fasta seqs_sorted.fasta otus.fa concatenated.good.fa')
    run('python /home/lee/bioinformatics/drive5/uc2otutab.py readmap.uc' + 
        ' > otutable.txt')
    # Perform a series of steps to classify OTUs by taxonomy with Greengenes
    # and align seqs in multiple alignment to create FastTree tree.
    cmd = ('mothur135 "#classify.seqs(fasta=otu.uchime.fa, ' + 
          'template=../database/gg_13_8_FWSET.fasta, processors=5, ' + 
          'taxonomy=../database/gg_13_8_FWSET.tax, cutoff=70)"')
    run(cmd)
    run('mothur135 "#align.seqs(fasta=otu.uchime.fa, ' + 
        'reference=../database/silva.v3v4.fasta)"')
    run('mothur135 "#screen.seqs(fasta=otu.uchime.align, criteria=90,' + 
        ' optimize=start-end)"')
    run('mothur135 "#filter.seqs(fasta=otu.uchime.good.align,' + 
        ' vertical=T, trump=.)"')
    run('mv otu.uchime.good.filter.fasta alignment.fasta')
    run('/media/DATA/programs/FastTreeMP -gtr -nt alignment.fasta' + 
        ' > FastTree2.tre')
    # Clean and organize
    run('mkdir ../UPARSE')
    run('mv otutable.txt alignment.fasta FastTree2.tre ../UPARSE')
    run('mv otu.uchime.gg* results.txt ../UPARSE')
    run('rm mothur* otu* readmap.uc')
    
def add_name_to_header(files):
    for i in files:
        name = i.replace('.fasta', '')
        cmd = ('sed \"-es/^>\(.*\)/>\\1;barcodelabel=' + name + ';/\" < ' + 
        i + ' > ' + name + '.fa')
 
        run(cmd)
        
# Simplify running bash commands
def run(cmd):
    p = subprocess.Popen(cmd, shell=True)
    p.communicate()
    
if __name__ == "__main__":
    main()
