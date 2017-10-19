# -*- coding: utf-8 -*-
"""
Created on Thu Oct 19 21:22:58 2017

@author: Quantum Liu
"""

import os,sys,re,traceback
import requests
import numpy as np
from multiprocessing import Pool,cpu_count,freeze_support
HOME='http://openaccess.thecvf.com/ICCV2017.py'
ROOT='http://openaccess.thecvf.com/'
r_paper=r'(<dt class="ptitle">.*?</dt>[\s\S]*?)<dt class="ptitle">'
r_url=r'<dt class="ptitle"><br><a href="(.*?html)"'
r_title=r'<meta name="citation_title" content="(.*?)">'
r_author=r'<meta name="citation_author" content="(.*?)">'
r_official_pdf='<meta name="citation_pdf_url" content="(.*?pdf)">'
r_abstract='<br><br><div id="abstract" >(.*?)</div>'
r_arxiv='[<a href="(.*?)">arXiv</a>]'

def check_name(name):
    rstr = r"[\/\\\:\*\?\"\<\>\|]"  # '/ \ : * ? " < > |'
    new_name = re.sub(rstr, "_", name)  # 替换为下划线
    return new_name

def check_format(path):
    sp=os.path.splitext(path)
    if not (sp[-1]=='.pdf'):
        new_path=os.path.join(sp[0],'.pdf')
        return new_path
    else:
        return path
    
def get_home():
    return requests.get(HOME)

def split_paper(res):
    return re.findall(r_paper,res.text)

def get_detial_url(paper_source):
    return ROOT+re.findall(r_url,paper_source)[0]

def get_all_papers(use_mp=True):
    res_h=get_home()
    paper_sources=split_paper(res_h)
    urls=[get_detial_url(s) for s in paper_sources]
    if use_mp:
        mp=Pool(min(8,max(cpu_count(),4)))
        results=[]
        for url in urls:
            results.append(mp.apply_async(Paper,(url,)))
        mp.close()
        mp.join()
        return {p.title:p for p in [result.get() for result in results]}
    else:
        return {p.title:p for p in [Paper(url) for url in urls]}

def doload_papers(papers,root='',use_mp=True):
    if use_mp:
        results=[]
        mp=Pool(min(8,max(cpu_count(),4)))
        for paper in papers:
            results.append(mp.apply_async(paper.download,(root,'',False)))
        mp.close()
        mp.join()
        num_official,num_arxiv=tuple(np.array([result.get() for result in results]).sum(0))
        print('Downloaded {} official version papers and {} arxiv version'.format(num_official,num_arxiv))
        
class Paper():
    def __init__(self,url):
        self.url_paper=url
        state=False
        time=1
        while not state:
            if time<5:
                try:
                    print('Trying getting paper from {} for time {}'.format(self.url_paper,time))
                    self.res=requests.get(url)
                except requests.exceptions.RequestException:
                    traceback.print_exc()
                    time+=1
                except KeyboardInterrupt:
                    raise KeyboardInterrupt
                self.text=self.res.text
                
                self.url_official_pdf=re.findall(r_official_pdf,self.text)[0]
                self.title=re.findall(r_title,self.text)
                self.abstract=re.findall(r_abstract,self.text)[0]
                self.authors=re.findall(r_author,self.text)
                self.check_arxiv()
                print('Title:\n{}\nAuthors:{}\n\n'.format(self.title,','.join(self.authors)))
                self.available=True
                self.ed_official,self.ed_arxiv=False,False
            else:
                Warning('Initing paper from {} failed'.format(self.url_paper))
                self.available=False
                
    def download(self,root='',path='',force=False):
        return self.download_official_pdf(root,path,force),self.download_arxiv(root,path,force)
        
    def download_arxiv(self,root='',path='',force=False):
        state=False
        time=1
        if self.available:
            if self.arxiv_available and ((not self.ed_arxiv) or force):
                while not state:
                    if time<5:
                        try:
                            print('Trying downloading arXiv version of paper {} for time {}'.format(self.title,time))
                            res=requests.get(self.url_arxiv_pdf)
                            state=True
                        except requests.exceptions.RequestException:
                            traceback.print_exc()
                            time+=1
                        except KeyboardInterrupt:
                            raise KeyboardInterrupt
                    else:
                        Warning('Offical arxiv pdf of paper {} is unavailable!\nReturn False!')
                        return False
                data=res.content
                path=check_format(path if path else os.path.join(root,check_name(self.title)+'_arxiv'))
                with open(os.path.abspath(path),'wb') as f:
                    f.write(data)
                self.ed_arxiv=True
                return True
        else:
            return False
    def download_official_pdf(self,root='',path='',force=False):
        state=False
        time=1
        if self.available:
            if (not self.ed_official) or force:
                while not state:
                    if time<5:
                        try:
                            print('Trying downloading official version of paper {} for time {}'.format(self.title,time))
                            res=requests.get(self.url_official_pdf)
                            text=res.text
                            state=True
                        except requests.exceptions.RequestException:
                            traceback.print_exc()
                            time+=1
                        except KeyboardInterrupt:
                            raise KeyboardInterrupt
                    else:
                        Warning('Offical pdf of paper {} is unavailable!\nReturn False!'.format(self.title))
                        return False
                if 'Not Found' in text:
                    Warning('Offical pdf of paper {} is unavailable!\nReturn False!'.format(self.title))
                    return False
                data=res.content
                path=check_format(path if path else os.path.join(root,check_name(self.title)+'_arxiv'))
                with open(os.path.abspath(path),'wb') as f:
                    f.write(data)
                self.ed_official=True
                return True
        else:
            return False
        
    def check_arxiv(self):
        result=re.findall(r_arxiv,self.text)
        if result:
            self.arxiv_available,self.url_arxiv_abs= True,result[0]
        else:
            self.arxiv_available,self.url_arxiv_abs= False,''
            
        if self.url_arxiv_abs:
            self.url_arxiv_pdf=self.url_arxiv_abs.replace('abs','pdf')
