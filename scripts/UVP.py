#! /usr/bin/python
"""

"""
import sys
import subprocess
import os
import types
import gzip
import yaml
import ConfigParser
import io
from datetime import datetime

class snp():

    def __init__(self, input, outdir, reference, name, paired,input2, verbose, argString):
        self.name               = name
        self.fOut1              = "Results"
        self.fOut               = self.fOut1 + "/" + outdir
        self.flog               = "QC"
        self.input              = input
        self.outdir             = self.fOut + "/tmp"
        self.tmp                = self.outdir + "/tmp"
        self.prinseq            = self.fOut + "/prinseq"
        self.fastqc            = self.fOut + "/fastqc"
        self.qualimap           = self.fOut + "/qualimap"
        self.kraken             = self.fOut + "/kraken"
        self.paired             = paired
        self.input2             = input2
        self.verbose            = verbose
        self.reference          = reference
        self.__finalVCF         = ''
        self.__annotation       = ''
        self.__final_annotation = ''
        self.__unclear          = ''
        self.__mixed            = ''
        self.__low              = ''

        # Create the output directory, and start the log file.
        self.__logged = False

        if not os.path.isfile(self.fOut1):
           self.__CallCommand('mkdir', ['mkdir', self.fOut1])

        self.__CallCommand('mkdir', ['mkdir', self.fOut])

        if not os.path.isfile(self.flog):
           self.__CallCommand('mkdir', ['mkdir', self.flog])

        self.__CallCommand('mkdir', ['mkdir', '-p', self.tmp])
        self.__CallCommand('mkdir', ['mkdir', '-p', self.fastqc])
        self.__CallCommand('mkdir', ['mkdir', '-p', self.qualimap])
        self.__CallCommand('mkdir', ['mkdir', '-p', self.kraken])
        self.__log     = self.fOut + "/" + self.name + ".log"

        with open("/uvp/scripts/config.yml", 'r') as ymlfile:
             cfg       = yaml.load(ymlfile)
        self.__lineage = self.fOut + "/" + self.name + ".lineage_report.txt"
        self.__logFH   = open(self.__log, 'w')
        self.__logFH.write(argString + "\n\n")
        self.__mlog    = self.flog + "/" + "master.log"
        self.__logFH2  = open(self.__mlog, 'a')
        self.__logged  = True
				
	# Format Validation
	self.__fastqval           = cfg['tools']['fastqvalidator']
        #fastq QC
        self.__fastqc            = cfg['tools']['fastqc']
        self.__kraken             = cfg['directories']['kraken']
        self.__krakendb           = cfg['directories']['krakendb']
        self.__krakenreport       = cfg['directories']['krakenreport']
        self.__pigz               = cfg['tools']['pigz']
        self.__unpigz             = cfg['tools']['unpigz']
        # Mapping
        self.__bwa                = cfg['tools']['bwa']
        self.__samtools           = cfg['tools']['samtools']
        self.__qualimap           = cfg['tools']['qualimap']
        # Picard-Tools
        self.__picard             = cfg['tools']['picard']
        # SNP / InDel Calling
        self.__gatk               = cfg['tools']['gatk']
        # Other
        self.__bcftools           = cfg['tools']['bcftools']
        self.__bedtools           = cfg['tools']['bedtools']
        self.__vcfannotate        = cfg['tools']['vcfannotate']
        self.__vcftools           = cfg['tools']['vcftools']
        self.__vcfutils           = cfg['tools']['vcfutils'] 
        self.__annotator          = cfg['tools']['annotator'] 
        self.__parser             = cfg['scripts']['parser']
        self.__lineage_parser     = cfg['scripts']['lineage_parser']
        self.__lineages           = cfg['scripts']['lineages']
        self.__excluded           = cfg['scripts']['excluded']
        self.__coverage_estimator = cfg['scripts']['coverage_estimator']
        self.resloci              = cfg['scripts']['resloci']
        self.__bedlist            = cfg['scripts']['bedlist']     
        self.__resis_parser       = cfg['scripts']['resis_parser']
        self.__del_parser         = cfg['scripts']['del_parser']
        self.mutationloci         = cfg['scripts']['mutationloci']
        self.snplist              = cfg['scripts']['snplist']
        self.__threads            = cfg['other']['threads']

    """ Shell Execution Functions """
    def __CallCommand(self, program, command):
        """ Allows execution of a simple command. """
        out = ""
        err = ""
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out,err = p.communicate()

        if (type(program) is list):
            o = open(program[1], 'w')
            o.write(out)
            o.close()
            out = ""
            program = program[0]
        
        if (self.__logged):
            self.__logFH.write('---[ '+ program +' ]---\n')
            self.__logFH.write('Command: \n' + ' '.join(command) + '\n\n')
            if out:
                self.__logFH.write('Standard Output: \n' + out + '\n\n')
            if err:
                self.__logFH.write('Standard Error: \n' + err + '\n\n')
        return 1
    
    """ Input Validation """
    def runVali(self):
        self.__ifVerbose("Validating Input file.")
        valiOut = self.fOut + "/validation"
        self.__CallCommand('mkdir', ['mkdir', '-p', valiOut]) 

        """ Validates format of input fastq files """	 			
	if self.paired:
           self.__CallCommand(['fastQValidator', valiOut + "/result1.out"], [self.__fastqval,'--file', self.input])
           self.__CallCommand(['fastQValidator', valiOut + "/result2.out"], [self.__fastqval,'--file', self.input2])
           output1 = valiOut + "/result1.out"
           output2 = valiOut + "/result2.out"
           self.__CallCommand(['cat', valiOut + "/result.out"], ['cat', output1, output2])
           self.__CallCommand('rm', ['rm', output1, output2 ])
        else:  
	   self.__CallCommand(['fastQValidator', valiOut + '/result.out'], [self.__fastqval,'--file', self.input])
        self.__CallCommand('mv', ['mv', valiOut + '/result.out', valiOut + '/Validation_report.txt'])	
	output = valiOut + "/Validation_report.txt"
        fh2 = open (output, 'r')
        for line in fh2:
            lined=line.rstrip("\r\n")
            if lined.startswith("Returning"):
               comments = lined.split(":")
               if comments[2] != " FASTQ_SUCCESS":
                  self.__CallCommand('mv', ['mv', self.input, self.flog])
                  self.__CallCommand('mv', ['mv', self.fOut, self.flog])
                  if self.paired:
                     self.__CallCommand('mv', ['mv', self.input2, self.flog])  
                  self.__logFH.write("Input not in fastq format\n")
                  i = datetime.now()
                  self.__logFH2.write(i.strftime('%Y/%m/%d %H:%M:%S') + "\t" + "Input:  " + self.input + "\t" + "not in fastq format\n")
                  sys.exit(1)

    """ Fastq QC """
    def runFastQC(self):
        self.__ifVerbose("Performing  FastQC.")
        self.__CallCommand('fastqc', [self.__fastqc, '--extract', '-t', self.__threads, '-o', self.fastqc, self.input])
        fastqname = os.path.basename(self.input)
        fastqcinput = fastqname.replace(".fastq.gz","_fastqc")
        fastqcOut = self.fastqc + "/" + fastqcinput + "/fastqc_data.txt"
        fh1 = open(fastqcOut, 'r')
        for line in fh1:
            lined = line.rstrip("\r\n")
            if lined.startswith(">>Basic"):
               fields = lined.split('\t')
               if fields[1] != 'pass':
                  i = datetime.now()
                  self.__logFH2.write(i.strftime('%Y/%m/%d %H:%M:%S') + "\t" + "Input:" + "\t" + self.input + "\t" + "Fastq file QC flag\n")
            break
        fh1.close()
        self.__CallCommand('rm', ['rm', '-r', self.fastqc + "/" + fastqcinput])

    """ Species specificity check """
    def runKraken(self):
        self.__ifVerbose("Running Kraken.")
        valiOut = self.fOut + "/validation"
        self.__logFH.write("########## Running Kraken. ##########\n")
        if self.paired:
           self.__CallCommand(['kraken', self.kraken + "/kraken.txt"],[self.__kraken, '--db', 
                               self.__krakendb, '--gzip-compressed', self.input, self.input2,
                               '--paired', '--fastq-input', '--threads', self.__threads, '--classified-out',
                                self.name + "_classified_Reads.fastq"])
           self.__CallCommand(['krakenreport', self.kraken + "/final_report.txt"],[self.__krakenreport, '--db',
                               self.__krakendb, self.kraken + "/kraken.txt"])
        else:
           self.__CallCommand(['kraken', self.kraken + "/kraken.txt"],[self.__kraken, '--db', 
                               self.__krakendb, '--gzip-compressed', self.input, '--fastq-input', 
                               '--threads', self.__threads, '--classified-out', self.name + "_classified_Reads.fastq"])                     
           self.__CallCommand(['krakenreport', self.kraken + "/final_report.txt"],[self.__krakenreport, '--db',
                               self.__krakendb, self.kraken + "/kraken.txt"])
        krakenOut = self.kraken + "/final_report.txt"
        cov = 0
        fh1 = open(krakenOut,'r')
        for lines in fh1:
            fields = lines.rstrip("\r\n").split("\t") 
            if fields[5].find("Mycobacterium tuberculosis") != -1:
               cov += float(fields[0])
        if cov < 90:
           self.__CallCommand('mv', ['mv', self.input, self.flog])
           self.__CallCommand('mv', ['mv', self.fOut, self.flog])
           self.__CallCommand('rm', ['rm', self.kraken + "/kraken.txt"])
           self.__logFH.write("not species specific\n")
           i = datetime.now()
           self.__logFH2.write(i.strftime('%Y/%m/%d %H:%M:%S') + "\t" + "Input:" + "\t" + self.input + "\t" + "not species specific\n")
           if self.paired:
              self.__CallCommand('mv', ['mv', self.input2, self.flog])
              self.__logFH2.write(i.strftime('%Y/%m/%d %H:%M:%S') + "\t" + "Input:" + "\t" + self.input2 + "\t" + "not species specific\n")
           sys.exit(2) 
    
    """ Aligners """ 
    def runBWA(self, bwa):
        """ Align reads against the reference using bwa."""
        self.__ranBWA = True
        self.__ifVerbose("Running BWA.")
        self.__logFH.write("########## Running BWA. ##########\n")
        bwaOut = self.outdir + "/bwa"
        self.__CallCommand('mkdir', ['mkdir', '-p', bwaOut])
        self.__ifVerbose("   Building BWA index.")
        self.__bwaIndex(bwaOut + "/index")
        self.__alnSam = bwaOut + "/bwa.sam"
        self.__bwaLongReads(bwaOut)
        self.__ifVerbose("") 
        self.__processAlignment()
          
    def __bwaIndex(self, out):
        """ Make an index of the given reference genome. """ 
        self.__CallCommand('mkdir', ['mkdir', '-p', out])
        self.__CallCommand('cp', ['cp', self.reference, out + "/ref.fa"])
        self.reference = out + "/ref.fa"
        self.__CallCommand('bwa index', [self.__bwa, 'index', self.reference])
        self.__CallCommand('CreateSequenceDictionary', ['java', '-jar', self.__picard, 
                           'CreateSequenceDictionary', 'R='+self.reference,'O='+ out + "/ref.dict"])
        self.__CallCommand('samtools faidx', [self.__samtools, 'faidx', self.reference ])

    def __bwaLongReads(self, out):
        """ Make use of bwa mem """
        if self.paired:
            self.__ifVerbose("   Running BWA mem on paired end reads.")
            self.__CallCommand(['bwa mem', self.__alnSam], [self.__bwa, 'mem','-t',self.__threads,'-R', 
                               "@RG\tID:" + self.name + "\tSM:" + self.name + "\tPL:ILLUMINA", 
                                self.reference, self.input, self.input2])
        else:
            self.__ifVerbose("   Running BWA mem on single end reads.")
            self.__CallCommand(['bwa mem', self.__alnSam], [self.__bwa, 'mem','-t', self.__threads, '-R', 
                               "@RG\tID:" + self.name + "\tSM:" + self.name + "\tPL:ILLUMINA", 
                                self.reference, self.input])       

    def __processAlignment(self):
        """ Filter alignment using GATK and Picard-Tools """
        self.__ifVerbose("Filtering alignment with GATK and Picard-Tools.")
        self.__logFH.write("########## Filtering alignment with GATK and Picard-Tools. ##########\n")
        GATKdir = self.outdir + "/GATK"
        self.__CallCommand('mkdir', ['mkdir', '-p', GATKdir])

        """ Convert SAM to BAM"""
        if (self.__ranBWA):
            self.__ifVerbose("   Running SamFormatConverter.")
            self.__CallCommand('SamFormatConverter', ['java', '-Xmx4g', '-jar', self.__picard, 'SamFormatConverter',  
                               'INPUT='+ self.__alnSam, 'VALIDATION_STRINGENCY=LENIENT', 
                               'OUTPUT='+ GATKdir +'/GATK.bam', ])
        else:
            self.__CallCommand('cp', ['cp', self.__alnSam, GATKdir +'/GATK.bam'])


        """ Run mapping Report and Mark duplicates using Picard-Tools"""
        self.__ifVerbose("   Running SortSam.")
        self.__CallCommand('SortSam', ['java', '-Xmx8g', '-Djava.io.tmpdir=' + self.tmp, '-jar', self.__picard, 'SortSam',  
                           'INPUT='+ GATKdir +'/GATK.bam', 'SORT_ORDER=coordinate', 'OUTPUT='+ GATKdir +'/GATK_s.bam', 
                           'VALIDATION_STRINGENCY=LENIENT', 'TMP_DIR=' + self.tmp])
        self.__ifVerbose("   Running Qualimap.")
        self.__CallCommand('qualimap bamqc', [self.__qualimap, 'bamqc', '-bam', GATKdir +'/GATK_s.bam', '-outdir', self.qualimap])
        self.__ifVerbose("   Running MarkDuplicates.")
        self.__CallCommand('MarkDuplicates', ['java', '-Xmx8g', '-jar', self.__picard, 'MarkDuplicates',  
                           'INPUT='+ GATKdir +'/GATK_s.bam', 'OUTPUT='+ GATKdir +'/GATK_sdr.bam',
                           'METRICS_FILE='+ GATKdir +'/MarkDupes.metrics', 'ASSUME_SORTED=true', 
                           'REMOVE_DUPLICATES=false', 'VALIDATION_STRINGENCY=LENIENT'])         
        self.__ifVerbose("   Running AddOrReplaceReadGroups.")
        self.__ifVerbose("   Running BuildBamIndex.")
        self.__CallCommand('BuildBamIndex', ['java', '-Xmx8g', '-jar', self.__picard, 'BuildBamIndex',  
                           'INPUT='+ GATKdir +'/GATK_sdr.bam', 'VALIDATION_STRINGENCY=LENIENT'])

        """ Re-alignment around InDels using GATK """
        self.__ifVerbose("   Running RealignerTargetCreator.")
        self.__CallCommand('RealignerTargetCreator', ['java', '-Xmx32g', '-jar', self.__gatk, '-T', 
                           'RealignerTargetCreator', '-I', GATKdir +'/GATK_sdr.bam', '-R', self.reference, 
                           '-o', GATKdir +'/GATK.intervals', '-nt', '12'])
        self.__ifVerbose("   Running IndelRealigner.")
        self.__CallCommand('IndelRealigner', ['java', '-Xmx4g', '-jar', self.__gatk, '-T', 'IndelRealigner', '-l', 
                           'INFO', '-I', GATKdir +'/GATK_sdr.bam', '-R', self.reference, '-targetIntervals', 
                           GATKdir +'/GATK.intervals', '-o', GATKdir +'/GATK_sdrc.bam'])
        self.__ifVerbose("   Running BaseRecalibrator.")
        self.__CallCommand('BaseRecalibrator', ['java', '-Xmx4g', '-jar', self.__gatk, '-T', 'BaseRecalibrator', 
                           '-I', GATKdir +'/GATK_sdrc.bam', '-R', self.reference, '--knownSites', 
                           self.snplist, '-o', GATKdir +'/GATK_Resilist.grp','-nct', '8'])
        self.__ifVerbose("   Running PrintReads.")
        self.__CallCommand('PrintReads', ['java', '-Xmx4g', '-jar', self.__gatk, '-T', 'PrintReads', 
                           '-I', GATKdir +'/GATK_sdrc.bam', '-R', self.reference, '-BQSR', 
                           GATKdir +'/GATK_Resilist.grp', '-o', GATKdir +'/GATK_sdrcr.bam','-nct', '8'])
        self.__ifVerbose("   Running SortSam.")
        self.__CallCommand('SortSam', ['java', '-Xmx8g', '-Djava.io.tmpdir=' + self.tmp, '-jar', self.__picard,'SortSam',  
                           'INPUT='+ GATKdir +'/GATK_sdrcr.bam', 'SORT_ORDER=coordinate', 'TMP_DIR=' + self.tmp, 
                           'OUTPUT='+ GATKdir +'/GATK_sdrcs.bam', 'VALIDATION_STRINGENCY=LENIENT'])
        self.__ifVerbose("   Running BuildBamIndex.")
        self.__CallCommand('BuildBamIndex', ['java', '-Xmx8g', '-jar', self.__picard, 'BuildBamIndex', 
                           'INPUT='+ GATKdir +'/GATK_sdrcs.bam', 'VALIDATION_STRINGENCY=LENIENT'])

        """ Filter out unmapped reads """
        self.__finalBam = self.fOut + '/'+ self.name + '_sdrcsm.bam'
        self.__ifVerbose("   Running samtools view.")
        self.__CallCommand('samtools view', ['samtools', 'view', '-bhF', '4', '-o', self.__finalBam, 
                           GATKdir +'/GATK_sdrcs.bam'])
        self.__ifVerbose("   Running BuildBamIndex.")
        self.__CallCommand('BuildBamIndex', ['java', '-Xmx8g', '-jar', self.__picard, 'BuildBamIndex', 'INPUT='+ self.__finalBam, 
                           'VALIDATION_STRINGENCY=LENIENT'])
        self.__ifVerbose("")
        self.__CallCommand('rm', ['rm', '-r', self.tmp])
    
    """ Callers """

    def runGATK(self):
        if os.path.isfile(self.__finalBam):
            self.__ifVerbose("Calling SNPs/InDels with GATK.")
            self.__logFH.write("########## Calling SNPs/InDels with GATK. ##########\n")
            GATKdir = self.outdir + "/GATK"
            samDir = self.outdir + "/SamTools"
            self.__CallCommand('mkdir', ['mkdir', '-p', samDir])

            """ Call SNPs/InDels with GATK """
            self.__ifVerbose("   Running UnifiedGenotyper.")
            self.__CallCommand('Pileup', ['java', '-Xmx4g', '-jar', self.__gatk, '-T', 'Pileup',
                               '-I', self.__finalBam, '-R', self.reference,'-o', self.fOut + "/" + self.name +'.mpileup',
                               '-nct', '6', '-nt', '4'])
            self.__CallCommand('UnifiedGenotyper', ['java', '-Xmx4g', '-jar', self.__gatk, '-T', 'UnifiedGenotyper', 
                               '-glm', 'BOTH', '-R', self.reference, '-I', self.__finalBam, '-o',  GATKdir +'/gatk.vcf', 
                               '-stand_call_conf', '20.0', '-stand_emit_conf', '20.0', '-nct', '6', '-nt', '4']) 
            self.__CallCommand(['vcf-annotate filter', self.fOut + "/" + self.name +'_GATK.vcf'], 
                               [self.__vcfannotate, '--filter', 'SnpCluster=3,10/Qual=20/MinDP=10/MinMQ=20', GATKdir +'/gatk.vcf'])
            self.__CallCommand(['vcftools remove-filtered-all', self.fOut + "/" + self.name +'_GATK_Resistance_filtered.vcf'], 
                                  [self.__vcftools, '--vcf', self.fOut + "/" + self.name +'_GATK.vcf',
                                  '--stdout', '--bed', self.resloci, '--remove-filtered-all', '--recode', '--recode-INFO-all'])
            self.__CallCommand(['vcftools remove-filtered-all', self.fOut + "/" + self.name +'_GATK_filtered.vcf'], 
                                   [self.__vcftools, '--vcf', self.fOut + "/" + self.name +'_GATK.vcf',
                                   '--stdout', '--exclude-bed', self.__excluded, '--remove-filtered-all', '--recode', '--recode-INFO-all'])
            self.__CallCommand(['samtools depth', samDir + '/coverage.txt'],
                                [self.__samtools,'depth', self.__finalBam])
            self.__CallCommand(['bedtools coverage', samDir + '/bed_coverage.txt' ],
                                ['bedtools','coverage', '-abam', self.__finalBam, '-b', self.__bedlist])
            self.__CallCommand(['sort', samDir + '/bed_sorted_coverage.txt' ],
                                ['sort', '-nk', '2', samDir + '/bed_coverage.txt'])

            """ Set final VCF file. """
            
            if not self.__finalVCF: 
                self.__finalVCF = self.fOut + "/" + self.name +'_GATK_filtered.vcf'
        else:
            # print error
            pass

    def runSamTools(self):
        """ Call SNPs and InDels using SamTools """
        if os.path.isfile(self.__finalBam):
            self.__ifVerbose("Calling SNPs/InDels with SamTools.")
            self.__logFH.write("########## Calling SNPs/InDels with SamTools. ##########\n")
            samDir = self.outdir + "/SamTools"
            self.__CallCommand('mkdir', ['mkdir', '-p', samDir])

            """ Call SNPs / InDels using mpileup, bcftools, vcfutils. """
            self.__ifVerbose("   Running samtools mpileup.")
            self.__CallCommand(['samtools mpileup', samDir + '/samtools.mpileup'], ['samtools', 'mpileup', '-Q', '20', '-q', '20', '-t', 'DP,DV,DPR', 
                               '-ugf', self.reference, self.__finalBam])
            self.__ifVerbose("   Running bcftools view.")
            self.__CallCommand(['bcftools view', samDir + '/samtools.vcf'], 
                               [self.__bcftools, 'call', '-vcf', 'GQ', samDir + '/samtools.mpileup'])
            self.__ifVerbose("   Running vcfutils.pl varFilter.")
            self.__CallCommand(['vcfutils.pl varFilter', samDir +'/SamTools.vcf'], 
                               [self.__vcfutils, 'varFilter', '-D1500', samDir + '/samtools.vcf'])
            self.__ifVerbose("   Filtering VCf file using vcftools.")
            self.__CallCommand(['vcf-annotate filter', self.fOut + "/" + self.name +'_SamTools.vcf'], 
                               ['vcf-annotate', '--filter', 'SnpCluster=3,10/Qual=20/MinDP=10/MinMQ=20', samDir +'/SamTools.vcf'])
            self.__CallCommand(['vcftools remove-filtered-all', self.fOut + "/" + self.name +'_SamTools_Resistance_filtered.vcf'], 
                                  [self.__vcftools, '--vcf', self.fOut + "/" + self.name +'_SamTools.vcf',
                                  '--stdout', '--bed', self.resloci, '--remove-filtered-all', '--recode', '--recode-INFO-all'])
            self.__CallCommand(['vcftools remove-filtered-all', self.fOut + "/" + self.name +'_SamTools_filtered.vcf'], 
                                   [self.__vcftools, '--vcf', self.fOut + "/" + self.name +'_SamTools.vcf',
                                   '--stdout', '--exclude-bed', self.__excluded, '--remove-filtered-all', '--recode', '--recode-INFO-all'])
            self.__CallCommand('mv', ['mv', samDir + '/samtools.mpileup', self.fOut + "/" + self.name + '.mpileup'])
            self.__CallCommand(['samtools depth', samDir + '/coverage.txt'],
                                [self.__samtools,'depth', self.__finalBam])
            self.__CallCommand(['bedtools coverage', samDir + '/bed_coverage.txt' ],
                                ['bedtools','coverage', '-abam', self.__finalBam, '-b', self.__bedlist])
            self.__CallCommand(['sort', samDir + '/bed_sorted_coverage.txt' ],
                                ['sort', '-nk', '2', samDir + '/bed_coverage.txt'])                 
            
            """ Set final VCF """
            if not self.__finalVCF: 
                self.__finalVCF = self.fOut + "/" + self.name +'_SamTools_filtered.vcf'     
        else:
            # print error  
            pass  
       
    def annotateVCF(self):
        """ Annotate the final VCF file """
        if self.__finalVCF:
           self.__ifVerbose("Annotating final VCF.")
           self.__CallCommand(['SnpEff', self.fOut + "/" + self.name +'_annotation.txt'],
                                ['java', '-Xmx4g', '-jar', self.__annotator, 'NC_000962', self.__finalVCF])
           self.__annotation = self.fOut + "/" + self.name +'_annotation.txt'
           self.__ifVerbose("parsing final Annotation.")
           self.__CallCommand(['parse annotation', self.fOut + "/" + self.name +'_Final_annotation.txt'],
                              ['python', self.__parser, self.__annotation, self.name, self.mutationloci])
           if os.path.isfile(self.fOut + "/" + self.name +'_SamTools_Resistance_filtered.vcf'):
              self.__CallCommand(['SnpEff', self.fOut + "/" + self.name +'_Resistance_annotation.txt'],
                                 ['java', '-Xmx4g', '-jar', self.__annotator, 'NC_000962', self.fOut + "/" + self.name +'_SamTools_Resistance_filtered.vcf']) 
              self.__ifVerbose("parsing final Annotation.")
              self.__CallCommand(['parse annotation', self.fOut + "/" + self.name +'_Resistance_Final_annotation.txt'],
                              ['python', self.__parser, self.fOut + "/" + self.name +'_Resistance_annotation.txt', self.name, self.mutationloci])
           elif os.path.isfile(self.fOut + "/" + self.name +'_GATK_Resistance_filtered.vcf'):
              self.__CallCommand(['SnpEff', self.fOut + "/" + self.name +'_Resistance_annotation.txt'],
                                 ['java', '-Xmx4g', '-jar', self.__annotator, 'NC_000962', self.fOut + "/" + self.name +'_GATK_Resistance_filtered.vcf']) 
              self.__ifVerbose("parsing final Annotation.")
              self.__CallCommand(['parse annotation', self.fOut + "/" + self.name +'_Resistance_Final_annotation.txt'],
                              ['python', self.__parser, self.fOut + "/" + self.name +'_Resistance_annotation.txt', self.name, self.mutationloci])
        else:
            self.__ifVerbose("Use SamTools, GATK, or Freebayes to annotate the final VCF.")

    def runLineage(self):
        """ Run lineage Analysis """
        self.__ifVerbose("Running Lineage Analysis")
        self.__final_annotation = self.fOut + "/" + self.name +'_Final_annotation.txt'
        self.__CallCommand(['lineage parsing', self.fOut + "/" + self.name +'_Lineage.txt'],
                              ['python', self.__lineage_parser, self.__lineages, self.__final_annotation, self.__lineage, self.name])
        count1 = 0
        count2 = 0
        count3 = 0
        fh1 = open(self.__lineage,'r')
        for line in fh1:
            lined = line.rstrip("\r\n")
            i = datetime.now()
            if "No Informative SNPs" in lined:
                self.__logFH2.write(i.strftime('%Y/%m/%d %H:%M:%S') + "\t" + "Input:" + "\t" + self.name + "\t" + "no clear lineage classification\n")
                self.__unclear = "positive"
            elif "no precise lineage" in lined:
                self.__logFH2.write(i.strftime('%Y/%m/%d %H:%M:%S') + "\t" + "Input:" + "\t" + self.name + "\t" + "no clear lineage classification\n")
                self.__mixed = "positive"
            elif "no concordance" in lined:
                self.__logFH2.write(i.strftime('%Y/%m/%d %H:%M:%S') + "\t" + "Input:" + "\t" + self.name + "\t" + "no clear lineage classification\n")
                self.__mixed = "positive"
        fh1.close()
        fh2 = open(self.fOut + "/" + self.name +'_Resistance_Final_annotation.txt','r')
        for lines in fh2:
            lined = lines.rstrip("\r\n").split("\t")
            if lined[16] == "rrs":
               count1 += 1
            elif lined[16] == "rrl":
               count2 += 1
            if lined[9] == "MNV":
               count3 += 1
        if count1 > 5 or count2 > 5 :
           self.__logFH2.write(i.strftime('%Y/%m/%d %H:%M:%S') + "\t" + "Input:" + "\t" + self.name + "\t" + "mixed species suspected\n")
           self.__mixed = "positive"
        if count3 > 0:
           self.__logFH2.write(i.strftime('%Y/%m/%d %H:%M:%S') + "\t" + "Input:" + "\t" + self.name + "\t" + "Block substitution inferred\n")
        fh2.close()
        
    def runCoverage(self):
        """ Run Genome Coverage Statistics """
        cov = ""
        notes = []
        dele = True

        self.__ifVerbose("Running Genome Coverage Statistics")
        samDir = self.outdir + "/SamTools"
        i = datetime.now()
        self.__CallCommand(['coverage estimator', self.fOut + "/" + self.name + '_Coverage.txt'],
                            ['python', self.__coverage_estimator, samDir + '/coverage.txt'])
        self.__CallCommand(['genome region coverage estimator', self.fOut + "/" + self.name + '_genome_region_coverage.txt'],
                            ['python', self.__resis_parser, samDir + '/bed_sorted_coverage.txt', samDir + '/coverage.txt'])
        fh2 = open(self.fOut + "/" + self.name + '_Coverage.txt','r')
        for line in fh2:
            if line.startswith("Average"):
               cov_str = line.split(":")
               cov = cov_str[1].strip(" ")
        if int(cov) < 10:
           self.__low = "positive"
           self.__logFH2.write(i.strftime('%Y/%m/%d %H:%M:%S') + "\t" + "Input:" + "\t" + self.name + "\t" + "low genome coverage depth\n")
        fh2.close()                  
        self.__CallCommand(['loci deletion parser', self.fOut + "/" + self.name + '_deleted_loci.txt'],
                            ['python', self.__del_parser, self.fOut + "/" + self.name, self.name, self.__bedlist])
        fh3 = open(self.fOut + "/" + self.name + '_deleted_loci.txt','r')
        for line in fh3:
            fields = line.rstrip("\r\n").split("\t")
            notes.append(fields[9])
        for keys in notes:
            if "Complete" in keys or "Partial" in keys:
               dele = False
        if dele == False:
           self.__logFH2.write(i.strftime('%Y/%m/%d %H:%M:%S') + "\t" + "Input:" + "\t" + self.name + "\t" + "gene deletion inferred\n")
           fh3.close()
        else:
          fh3.close()
          self.__CallCommand('rm', ['rm',  self.fOut + "/" + self.name + '_deleted_loci.txt']) 
         
    def cleanUp(self):
        """ Clean up the temporary files, and move them to a proper folder. """
        self.__CallCommand('rm', ['rm', '-r', self.outdir])
        self.__CallCommand('rm', ['rm',  self.fOut + "/" + self.name +'_annotation.txt'])
        self.__CallCommand('rm', ['rm',  self.fOut + "/" + self.name +'_Resistance_annotation.txt'])
        self.__CallCommand('rm', ['rm',  self.fOut + '/'+ self.name + '_sdrcsm.bai'])
        self.__CallCommand('rm', ['rm',  self.__finalBam])
        self.__CallCommand('rm', ['rm',  self.kraken + "/kraken.txt"])
        if self.__mixed == "positive":
           self.__CallCommand('mv', ['mv', self.fOut, self.flog])
        if self.__unclear == "positive":
           self.__CallCommand('mv', ['mv', self.fOut, self.flog])
        if self.__low == "positive":
           self.__CallCommand('mv', ['mv', self.fOut, self.flog])
    def __ifVerbose(self, msg):
        """ If verbose print a given message. """
        if self.verbose: print msg