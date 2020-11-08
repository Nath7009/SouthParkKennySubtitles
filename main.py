# -*- coding: utf-8 -*-
"""
Created on Fri Oct 30 21:38:18 2020

@author: Nathan
"""

import requests
import os
import srt
import subprocess
import datetime
from fuzzywuzzy import fuzz
from bs4 import BeautifulSoup
from glob import glob



def get_dialogs(html_link):
    page = requests.get(html_link)
    html_text = str(page.content);
    html_text = html_text.replace('[', " ")
    html_text = html_text.replace(']', " ")
    html_text = html_text.replace('\\n', "")
    soup = BeautifulSoup(html_text, features="lxml")
    
    for tag in soup.find_all('i'):
        tag.replaceWith('')
        
    dialog = []
    i=0
    #for act in soup.find_all("table", {"class" : "wikitable bgrevo"}):
    for act in soup.find_all("table"):
        for tr  in act.find_all('tr'):
            if len(tr.find_all("th", text = True)) == 1 and len(tr.find_all("td")) == 1 : #Dialog
               #print(tr.find_all("th"), tr.find_all("td"))
               dialog.append([])
               dialog[i].append(tr.find_all("th")[0].get_text().lower())
               dialog[i].append(tr.find_all("td")[0].get_text())
               i+=1
            elif len(tr.find_all("td")) == 2 and tr.find_all("td")[0].get_text() != "":
                dialog.append([])
                dialog[i].append(tr.find_all("td")[0].get_text().lower())
                dialog[i].append(tr.find_all("td")[1].get_text())
                i+=1
                
    return dialog

def extract_subtitles(filename):
    filepath = "temp/subtitles.srt"
    if os.path.exists(filepath):
        os.remove(filepath)
      
    command = 'ffmpeg -loglevel panic -i "' + filename + '" -map 0:4 ' + filepath
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    process.wait()
    f = open(filepath, "r")
    subtitles = srt.parse(f.read())
    #print(len(list(subtitles)))
    return subtitles

def search_subtitle(subtitles, line):
    i = 0;
    for sub in subtitles:
        
        if fuzz.ratio(str(sub.content).lower(), line.lower()) > 80:
            #print(line, sub, str(fuzz.ratio(str(sub.content).lower(), line.lower())))
            return i
        elif fuzz.partial_ratio(str(sub.content).lower(), line.lower()) > 80:
            return i
        i+=1
    return -1
        

def get_kenny_lines(text):
    lines = []
    i = 0
    for line in text:
        if 'kenny' in line[0] :
            lines.append(i)
            line[1] = line[1].replace("\\", "")
        i+=1
    print(str(len(lines)) + " kenny lines found")
    return lines



def replace_line(dialogs, ind, line, subtitles):
    if ind == len(subtitles):
        ind-=1
        
    start_time = subtitles[ind].end
    if ind + 1 < len(subtitles):
        end_time = subtitles[ind + 1].start
    else:
        end_time = subtitles[ind].end + datetime.timedelta(0,2)
    
    sub = srt.Subtitle(ind + 2, start_time, end_time, dialogs[line][1])
    
    for i in range(ind + 1, len(subtitles)): #Moving all subtitles back
        subtitles[i].index+=1
    
    subtitles.insert(ind + 1, sub)
    return subtitles

def insert_kenny_lines(dialogs, subtitles):
    lines = get_kenny_lines(dialogs)
    #lines.reverse()
    for line in lines:
        #print("Searching line " + str(line))
        found = False
        offset = 1
        
        while not found and (line >= offset or line + offset < len(dialogs)): #Search for string before and after
        #End the while when all possibilities have been depleted
            if line >= offset:
                ind = search_subtitle(subtitles, dialogs[line-offset-1][1]) #Search the subtitles for the lines before
                if ind > 0:
                    subtitles = replace_line(dialogs, ind + offset, line, subtitles)
                    found = True
            
            if line + offset + 1 < len(dialogs) and not found:
                ind = search_subtitle(subtitles, dialogs[line+offset-1][1]) #Search the subtitles for the lines after
                if ind > 0:
                    subtitles = replace_line(dialogs, ind - offset, line, subtitles)
                    found = True
            
            
            offset+=1
            
        if not found:
            print("Could not find line : " + dialogs[line][1])
        '''
        ind = search_subtitle(subtitles, dialogs[line-1][1]) #Search the subtitles for the line just before

        if ind < 0 and len(dialogs) > line: #To prevent out of range
            ind = search_subtitle(subtitles, dialogs[line+1][1]) #Search the subtitles for the line just after
            if ind < 0:
                print("Could not find line : " + dialogs[line][1])
                pass
            else:
                #print("Line found", dialogs[line][1])
                start_time = subtitles[ind - 1].end
                end_time = subtitles[ind].start
                
                sub = srt.Subtitle(ind + 1, start_time, end_time, dialogs[line][1])
                
                for i in range(ind, len(subtitles)): #Moving all subtitles back
                    subtitles[i].index+=1
                
                subtitles.insert(ind, sub)
        elif ind > 0:
            #print("Line found", dialogs[line][1])
            start_time = subtitles[ind].end
            end_time = subtitles[ind + 1].start
            
            sub = srt.Subtitle(ind+2, start_time, end_time, dialogs[line][1])
            
            for i in range(ind+1, len(subtitles)): #Moving all subtitles back
                subtitles[i].index+=1
                
            subtitles.insert(ind+1, sub)
        '''
    return subtitles

def rewrite_subtitles(new_sub, filename, output):
    new_srt = srt.compose(new_sub)
    filepath = "temp/subtitles.srt"
    if os.path.exists(filepath):
        os.remove(filepath)
    
    file = open(filepath, "w")
    file.write(new_srt)
    file.flush()
    file.close()
    #command = 'ffmpeg  -i "' + filename + '" -sub_charenc "UTF-8" -f srt -i "' + filename + '" -map 0:0 -map 0:1 -map 1:0 -c:v copy -c:a copy -c:s srt "' + output + '"'
    #command = 'ffmpeg -i "' + filename + '" -sub_charenc "UTF-8" -i "' + filepath + '" -map 0:v -map 0:a -c copy -map 1 -c:s:0 srt -metadata:s:s:0 language=angd "' + output + '"'
    #process = subprocess.Popen(command, shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    command = 'ffmpeg -i "' + filename + '" -sub_charenc "UTF-8" -i "' + filepath + '" -map 0:v -map 0:a -map 0:s -c copy -map 1 -c:s:3 srt -metadata:s:s:3 language=eng-kenny "' + output + '"'    
    process = subprocess.Popen(command, shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    process.wait()

def get_links():
    page = requests.get('https://transcripts.fandom.com/wiki/South_Park')
    
    
    html_text = str(page.content)
    print(len(html_text))
    html_text = html_text[html_text.find('<span class="mw-headline" id="Season_1">Season 1</span>'):]
    print(len(html_text))
    html_text = html_text[:html_text.find('<span class="mw-headline" id="Others">Others</span>')]
    print(len(html_text))
    
    soup = BeautifulSoup(html_text, features="lxml")
    
    
    links = []
    i = 0
    for div in soup.find_all('div'):
        links.append([])
        for link in div.find_all('a'):
            #print(link)
            links[i].append('https://transcripts.fandom.com' + str(link.get('href')))   
        i+=1
        
    return links

links = get_links()


dialogs = get_dialogs(links[0][3])
subs = extract_subtitles("South Park S01E04 MULTi 1080p BluRay x264-GLaDOS.mkv")
subs_array = list(subs)
new_subs = insert_kenny_lines(dialogs, subs_array)
rewrite_subtitles(new_subs, "South Park S01E04 MULTi 1080p BluRay x264-GLaDOS.mkv", "out/South Park S01E04 MULTi 1080p BluRay x264-GLaDOS.mkv")

i=0
for folder in glob("Y:\Series\South Park S01-S21 MULTi 1080p BluRay x264-GLaDOS/*/"):
    fol = folder[3:]
    follist = fol.split("\\")
    if not os.path.exists("Y:\Series\out\\" + follist[2]):
        os.mkdir("Y:\Series\out\\" + follist[2])
    files = glob(folder+"/*.mkv")
    j=0
    for file in files:
        print(i,j)
        dialogs = get_dialogs(links[i][j])
        subs = extract_subtitles(file)
        subs_array = list(subs)
        new_subs = insert_kenny_lines(dialogs, subs_array)
        filelist = file.split("\\")
        rewrite_subtitles(new_subs, file, "Y:\Series/out/" + filelist[3] + "\\" + filelist[4])
        j+=1
    i+=1


