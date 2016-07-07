import sys
import re
import os
from os.path import isfile
import fnmatch
import argparse
import csv
from datetime import datetime, timedelta
import random

from nltk.stem.wordnet import WordNetLemmatizer
from nltk.corpus import stopwords


from sets import Set
from commit import commit


#import util


from os.path import dirname
sys.path.append(os.path.join(dirname(__file__),'..','util'))


import Util
from ConfigInfo import ConfigInfo

#----------------------------------------------------#

delim = '<<|>>'

extn2tag = { '.c' : 'c', \
        '.cpp' : 'cpp', '.cpp_' : 'cpp', '.cpp1' : 'cpp', '.cpp2' : 'cpp', '.cppclean' : 'cpp', '.cpp_NvidiaAPI_sample' : 'cpp', '.cpp-s8inyu' : 'cpp', '.cpp-woains' : 'cpp', \
        '.cs' : 'csharp', '.csharp' : 'csharp',  \
        '.m' : 'objc', \
        '.java' : 'java', \
        '.scala' : 'scala', '.scla' : 'scala', \
        '.go' : 'go', \
        '.javascript' : 'javascript', '.js' : 'javascript', \
        '.coffee' : 'coffeescript', '.coffeescript' : 'coffeescript', \
        '.ts' : 'typescript', '.typescript' : 'typescript', \
        '.rb'  : 'ruby', \
        '.php' : 'php', \
        '.pl' : 'perl', \
        '.py' : 'python', \
        '.sh' : 'shell', '.SH' : 'shell', '.ksh' : 'shell', '.bash' : 'shell', '.bat' : 'shell',  '.bats' : 'shell', \
        '.cljx' : 'clojure', '.cljscm' : 'clojure', '.clj' : 'clojure', '.cljc': 'clojure', '.cljs' : 'clojure', \
        '.css' : 'css', \
        '.erl' : 'erlang', \
        '.hs' : 'haskell'
        }


#----------------------------------------------------#


lmtzr = WordNetLemmatizer()
stoplist = stopwords.words('english')

def if_bug(text):
    global lmtzr
    global stoplist

    isBug = False

    text = text.lower()

    text = text.replace('error handl','')

    imp_words = [lmtzr.lemmatize(word) for word in text.lower().split() \
            if ((word not in stoplist)) ]
    bug_desc = ' '.join([str(x) for x in imp_words])

    if re.search(Util.ERR_STR, '\b'+bug_desc+'\b', re.IGNORECASE):
        isBug = True
    

    return isBug

#----------------------------------------------------#

def get_time(commit_date):

    if len(commit_date.strip().rsplit(" ",1)) != 2:
        return ""
    d, t = commit_date.strip().rsplit(" ",1)
    date_object = datetime.strptime(d, '%a %b %d %H:%M:%S %Y')
    h = int(t[1:3])
    m = int(t[4:6])
    if t[0]=='-':
        delta = date_object + timedelta(hours=h, minutes=m)
    else:
        delta = date_object - timedelta(hours=h, minutes=m)

    return str(delta)

#----------------------------------------------------#

class ghProcNoPatch:

    tag2xml = {}

    def __init__(self, project, no_merge_log, no_stat_log, config_file, bug_db=None):

        global CSV

        self.noMergeLog = no_merge_log
        self.noStatLog = no_stat_log
        self.configInfo = ConfigInfo(config_file) 
        self.extBugDb = bug_db

        self.project = project
        self.sha2commit = {}


    def parse(self, bug_only=False):

        self.parse_no_merge()
        self.parse_no_stat(bug_only)
        self.dump(bug_only)


    def dump(self, bug_only):

        if self.configInfo.CSV is False:
            return
            
        out_file = os.path.join(self.project, "ChangeSummaryNoPatch.csv")
        
        inf1=open(out_file,'w')
            
        for sha, co in self.sha2commit.iteritems():
          for ch in co.changes:
            insertion, deletion, file_name, language = ch.get() 
            if "test" in file_name:
              is_test = "True"
            else:
              is_test = "False"
              
            print (',').join((co.project, co.sha, \
                language, file_name, is_test, \
                co.committer, co.commit_date, co.author, co.author_date, \
                insertion,deletion))

            
        
    


    def dumpLog(self, sha, committer, commit_date, author, author_date, change_files):

        if sha is None:
            return False

        if self.sha2commit.has_key(sha):
            print "!!! sould not have this key"

        project = self.project.split(os.sep)[-1]
        co  = commit(project, sha)
        co.committer = committer
        co.commit_date = commit_date
        co.author = author
        co.author_date = author_date

        for ch in change_files:
            insertion, deletion, file_name = ch[0], ch[1], ch[2]
            lang_extension = os.path.splitext(file_name)[1].strip().lower()
            tag = extn2tag.get(lang_extension, None)

            if not tag is None:
                co.addChange(insertion, deletion, file_name, tag)
                
        self.sha2commit[sha] = co


    def parse_no_merge(self):

        global delim

        sha         = None
        committer   = None
        commit_date = None
        author      = None
        author_date = None
        is_dump = False

        change_files = []

        for line in open(self.noMergeLog, 'r'):

            line = line.strip()

            if line.startswith('>>>>>>>>>>>> '):
                line = line.split('>>>>>>>>>>>> ')[1]

                self.dumpLog(sha, committer, commit_date, author, author_date, change_files)

                del change_files[:]

                line_split = line.split(delim)

                sha, project, committer, commit_date, author, author_date = line_split[0:6]

                sha = sha.strip()

                commit_date = get_time(commit_date)
                author_date = get_time(author_date)

                author = author.decode('ascii', 'ignore').strip()
                committer = committer.decode('ascii', 'ignore').strip()


            elif re.match(r'\d+\t\d+\t', line) and (len(line.split('\t')) == 3):
                insertion, deletion, file_name = line.split('\t')
                extension = os.path.splitext(file_name)[1].strip().lower()
                change_files.append((insertion, deletion, file_name))

            else:
                pass

        self.dumpLog(sha, committer, commit_date, author, author_date, change_files)


    def dumpMssg(self, sha, subject, body, bug_only):

        if sha is None:
            return False

        co = self.sha2commit.get(sha)
        if co is None:
            print "!!! sould have this sha"
            return

        is_bug = False

        proj  = self.project.split(os.sep)[-1]
        
        issue = None
        
        if not self.extBugDb is None:
          issue = self.extBugDb.get((proj,sha))
      
        if issue == 'Bug':
            is_bug = True
        else:
            is_bug |= if_bug(subject)
            is_bug |= if_bug(body)

        co.subject = subject
        co.body    = body
        co.isbug   = is_bug

        

    def parse_no_stat(self, bug_only):

        global delim

        sha         = None
        subject     = None
        body        = None
        is_dump = False

        change_files = []

        for line in open(self.noStatLog, 'r'):

            line = line.strip()

            if line.startswith('>>>>>>>>>>>> '):
                line = line.split('>>>>>>>>>>>> ')[1]

                self.dumpMssg(sha, subject, body, bug_only)
                #is_dump |= self.dumpLog(sha, committer, commit_date, author, author_date, change_files)

                del change_files[:]

                line_split = line.split(delim)

                sha, project, subject, body = line_split[0:4]

                sha = sha.strip()

                body = body.decode('ascii', 'ignore').strip()

                if 'Signed-off-by:' in body:
                    body = body.partition('Signed-off-by:')[0]

                subject = subject.decode('ascii', 'ignore').strip()
                if 'Signed-off-by:' in subject:
                    subject = subject.partition('Signed-off-by:')[0]

                body = body.decode('ascii', 'ignore').strip()
                subject = subject.decode('ascii', 'ignore').strip()

            else:
                b = line.decode('ascii', 'ignore')
                b = b.rstrip(delim)
                if 'Signed-off-by:' in b:
                    #print "body : " , b.partition('Signed-off-by:')
                    b = b.partition('Signed-off-by:')[0]
                body += " " + b

        self.dumpMssg(sha, subject, body, bug_only)



# ---------------------------------------------------------------- #

def test():
    print "ghProcNoPatch"

    project = "/localtmp/feng/defects4j_origRepos/joda-time"
    no_merge = os.path.join(project,'no_merge_log.txt')
    no_stat = os.path.join(project,'no_stat_log.txt')
    config_file = 'test_conf.ini'
    pl = ghProcNoPatch(project, no_merge, no_stat, config_file)
    pl.parse(False)
    
    

if __name__ == "__main__":
  test()
