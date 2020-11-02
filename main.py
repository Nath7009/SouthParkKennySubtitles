# -*- coding: utf-8 -*-
"""
Created on Fri Oct 30 21:38:18 2020

@author: Nathan
"""

import requests
import os
import srt
import subprocess
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
            #if(len(tr.find_all("th", text = True)) == 1 and len(tr.find_all("td", text = True)) == 1): #Dialog
            if len(tr.find_all("th", text = True)) == 1 and len(tr.find_all("td")) != 0 : #Dialog
               #print(tr.find_all("th"), tr.find_all("td"))
               dialog.append([])
               dialog[i].append(tr.find_all("th")[0].get_text().lower())
               dialog[i].append(tr.find_all("td")[0].get_text())
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
        i+=1
    print('Could not find matching string : ' + line)
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


def insert_kenny_lines(dialogs, subtitles):
    lines = get_kenny_lines(dialogs)

    for line in lines:
        print("Searching line " + str(line))
        ind = search_subtitle(subtitles, dialogs[line-1][1]) #Search the subtitles for the line just before

        if ind < 0:
            ind = search_subtitle(subtitles, dialogs[line+1][1]) #Search the subtitles for the line just after
            if ind < 0:
                pass
            else:
                print("Line found", dialogs[line][1])
                start_time = subtitles[ind - 1].end
                end_time = subtitles[ind].start
                
                sub = srt.Subtitle(ind + 1, start_time, end_time, dialogs[line][1])
                
                for i in range(ind, len(subtitles)): #Moving all subtitles back
                    subtitles[i].index+=1
                
                subtitles.insert(ind, sub)
        else:
            print("Line found", dialogs[line][1])
            start_time = subtitles[ind].end
            end_time = subtitles[ind + 1].start
            
            sub = srt.Subtitle(ind+2, start_time, end_time, dialogs[line][1])
            
            for i in range(ind+1, len(subtitles)): #Moving all subtitles back
                subtitles[i].index+=1
                
            subtitles.insert(ind+1, sub)
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
    command = 'ffmpeg -loglevel panic -i "' + filename + '" -sub_charenc "UTF-8" -i "' + filepath + '" -map 0:v -map 0:a -c copy -map 1 -c:s:0 srt -metadata:s:s:0 language=angd "' + output + '"'
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
dialogs = get_dialogs(links[0][0])

i=0
j=0
for folder in glob("in/*/"):
    for file in glob(folder+"/*"):
        dialogs = get_dialogs(links[i][j])
        subs = extract_subtitles(file)
        subs_array = list(subs)
        new_subs = insert_kenny_lines(dialogs, subs_array)
        rewrite_subtitles(new_subs, file, "out/" + folder[3:] + "/" + file)
        j+=1
    i+=1


