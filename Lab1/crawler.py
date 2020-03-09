# Author: Michal Tomczyk
# Author: Michal Tomczyk
# michal.tomczyk@cs.put.poznan.pl
# Poznan University of Technology
# Institute of Computing Science
# Laboratory of Intelligent Decision Support Systems
#-------------------------------------------------------------------------
import urllib.request as req
import sys
import os
from html.parser import HTMLParser
import numpy as np

#-------------------------------------------------------------------------
### generatePolicy classes
  
class Parser (HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.output_list = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.output_list.append(dict(attrs).get('href'))

class LIFO_Policy:
    def __init__(self, c):
        self.queue = list()
        self.queue.extend(c.seedURLs)

    def getURL(self, c, iteration):
        if len(self.queue) == 0:
            self.queue = list()
            self.queue.extend(c.seedURLs)
        return self.queue.pop() 
            
    def updateURLs(self, c, retrievedURLs, retrievedURLsWD, iteration):
        pList = list()
        pList.extend(retrievedURLs)
        pList.sort(key = lambda url: url[len(url) - url[::-1].index('/'):])
        self.queue.extend(pList)

class FIFO_Policy:
    def __init__(self, c):
        self.queue = list()
        self.queue.extend(c.seedURLs)

    def getURL(self, c, iteration):
        if len(self.queue) == 0:
            self.queue = list()
            self.queue.extend(c.seedURLs)
        return self.queue.pop(0)
            
    def updateURLs(self, c, retrievedURLs, retrievedURLsWD, iteration):
        pList = list()
        pList.extend(retrievedURLs)
        pList.sort(key = lambda url: url[len(url) - url[::-1].index('/'):])
        self.queue.extend(pList)

class LIFO_Cycle_Policy:
    def __init__(self, c):
        self.queue = list()
        self.queue.extend(c.seedURLs)
        self.fetched = set()

    def getURL(self, c, iteration):
        while self.queue[-1] in self.fetched:
            self.queue.pop()
            if len(self.queue) == 0:
                self.queue = list()
                self.queue.extend(c.seedURLs)
                self.fetched.clear()
        
        popped = self.queue.pop()
        self.fetched.add(popped)
        return popped
            
    def updateURLs(self, c, retrievedURLs, retrievedURLsWD, iteration):
        pList = list()
        pList.extend(retrievedURLs)
        pList.sort(key = lambda url: url[len(url) - url[::-1].index('/'):])
        self.queue.extend(pList)


class LIFO_Authority_Policy:
    def __init__(self, c):
        self.queue = list()
        self.queue.extend(c.seedURLs)
        self.fetched = set()
        self.queue_empty = False

    def getURL(self, c, iteration):
        if not self.queue_empty:
            while self.queue[-1] in self.fetched:
                self.queue.pop()
                if len(self.queue) == 0:
                    self.queue_empty = True
                    break

        if self.queue_empty:
            res = dict()
            for val in c.incomingURLs:
                res[val] = len(c.incomingURLs[val]) + 1
            res_sum = sum(res.values())
            prob = [i / res_sum for i in res.values()]
            return np.random.choice(list(res.keys()), p = prob)
        else:
            popped = self.queue.pop()
            self.fetched.add(popped)
            return popped
            
    def updateURLs(self, c, retrievedURLs, retrievedURLsWD, iteration):
        pList = list()
        pList.extend(retrievedURLs)
        pList.sort(key = lambda url: url[len(url) - url[::-1].index('/'):])
        self.queue.extend(pList)
        
    
#-------------------------------------------------------------------------
# Data container
class Container:
    def __init__(self):
        # The name of the crawler"
        self.crawlerName = "IRbot"
        # Example ID
        self.example = "exercise3"
        # Root (host) page
        self.rootPage = "http://www.cs.put.poznan.pl/mtomczyk/ir/lab1/" + self.example
        # Initial links to visit
        self.seedURLs = ["http://www.cs.put.poznan.pl/mtomczyk/ir/lab1/"
            + self.example + "/s0.html"]
        # Maintained URLs
        self.URLs = set([])
        # Outgoing URLs (from -> list of outgoing links)
        self.outgoingURLs = {}
         # Incoming URLs (to <- from; set of incoming links)
        self.incomingURLs = {}
        # Class which maintains a queue of urls to visit. 
        self.generatePolicy = LIFO_Authority_Policy(self)
        # Page (URL) to be fetched next
        self.toFetch = None
        # Number of iterations of a crawler. 
        self.iterations = 50

        # If true: store all crawled html pages in the provided directory.
        self.storePages = True
        self.storedPagesPath = "./" + self.example + "/pages/"
        # If true: store all discovered URLs (string) in the provided directory
        self.storeURLs = True
        self.storedURLsPath = "/" + self.example +"/urls/"
        # If true: store all discovered links (dictionary of sets: from->set to),
        # for web topology analysis, in the provided directory
        self.storeOutgoingURLs = True
        self.storedOutgoingURLs = "/" + self.example + "/outgoing/"
        # Analogously to outgoing
        self.storeIncomingURLs = True
        self.storedIncomingURLs = "/" + self.example + "/incoming/"
        
        
        # If True: debug
        self.debug = False
        
def main():

    # Initialise data
    c = Container()
    # Inject: parse seed links into the base of maintained URLs
    inject(c)
    
    # Iterate...
    for iteration in range(c.iterations):
    
        if c.debug: 
            print("=====================================================")
            print("Iteration = " + str(iteration + 1) )
            print("=====================================================")
        # Prepare a next page to be fetched
        generate(c, iteration)
        if (c.toFetch == None):
            if c.debug:
                print("   No page to fetch!")
            continue
                
        # Generate: it downloads html page under "toFetch URL"
        page = fetch(c)
    
        if page == None:
            if c.debug:
                print("   Unexpected error; skipping this page")
            removeWrongURL(c)
            continue
            
        # Parse file
        htmlData, retrievedURLs = parse(c, page, iteration)
        
        # Store pages
        if c.storePages:
            storePage(c, htmlData)
        
        ### normalise retrievedURLs
        retrievedURLs = getNormalisedURLs(retrievedURLs)
        
        ### update outgoing/incoming links
        updateOutgoingURLs(c, retrievedURLs)
        updateIncomingURLs(c, retrievedURLs)
        
        ### Filter out some URLs
        retrievedURLs = getFilteredURLs(c, retrievedURLs)
        
        ### removeDuplicates
        retrievedURLsWD = removeDuplicates(c, retrievedURLs)
        
        ### update urls
        c.generatePolicy.updateURLs(c, retrievedURLs, retrievedURLsWD, iteration)
        
        # Add newly obtained URLs to the container   
        if c.debug:
            print("   Maintained URLs...")
            for url in c.URLs:
                print("      " + str(url))
        
        if c.debug:
            print("   Newly obtained URLs (duplicates with maintaines URLs possible) ...")
            for url in retrievedURLs:
                    print("      " + str(url))
        if c.debug:
            print("   Newly obtained URLs (without duplicates) ...")
            for url in retrievedURLsWD:
                    print("      " + str(url))        
            for url in retrievedURLsWD:
                c.URLs.add(url)

    # store urls
    if c.storeURLs:
        storeURLs(c)
    if c.storeOutgoingURLs:
        storeOutgoingURLs(c)
    if c.storeIncomingURLs:
        storeIncomingURLs(c)            
    

#-------------------------------------------------------------------------
# Inject seed URL into a queue (DONE)
def inject(c):
    for l in c.seedURLs:
        if c.debug: 
            print("Injecting " + str(l))
        c.URLs.add(l)

#-------------------------------------------------------------------------
# Produce next URL to be fetched (DONE)
def generate(c, iteration):
    url = c.generatePolicy.getURL(c, iteration)
    if url == None:
        if c.debug:
            print("   Fetch: error")
        c.toFetch = None
        return None
    # WITH NO DEBUG!
    print("   Next page to be fetched = " + str(url)) 
    c.toFetch = url
    

#-------------------------------------------------------------------------
# Generate (download html) page (DONE)
def fetch(c):
    URL = c.toFetch
    if c.debug: 
        print("   Downloading " + str(URL))
    try:
        opener = req.build_opener()
        opener.addheadders = [('User-Agent', c.crawlerName)]
        webPage = opener.open(URL)
        return webPage
    except:
        return None 
        
#-------------------------------------------------------------------------  
# Remove wrong URL (TODO) DONE
def removeWrongURL(c):
    c.URLs.remove(c.toFetch)
    
    
#-------------------------------------------------------------------------  
# Parse this page and retrieve text (whole page) and URLs (TODO) DONE
def parse(c, page, iteration):
    # data to be saved (DONE)
    htmlData = page.read()
    # obtained URLs (TODO) DONE
    p = Parser()
    p.feed(str(htmlData))
    retrievedURLs = set(p.output_list)
    if c.debug:
        print("   Extracted " + str(len(retrievedURLs)) + " links")

    return htmlData, retrievedURLs

#-------------------------------------------------------------------------  
# Normalise newly obtained links (TODO) DONE
def getNormalisedURLs(retrievedURLs):
    tmp_set = set()
    for elem in retrievedURLs:
        tmp_set.add(elem.lower())  
    # retrievedURLs = tmp_set
    return tmp_set
    
#-------------------------------------------------------------------------  
# Remove duplicates (duplicates) (TODO) DONE
def removeDuplicates(c, retrievedURLs):
    tmp_set = set()
    for elem in retrievedURLs:
        if elem not in c.URLs:
            tmp_set.add(elem)
    # retrievedURLs = tmp_set
    return tmp_set

#-------------------------------------------------------------------------  
# Filter out some URLs (TODO) DONE
def getFilteredURLs(c, retrievedURLs):
    toLeft = set([url for url in retrievedURLs if url.lower().startswith(c.rootPage)])
    if c.toFetch in toLeft:
        toLeft.remove(c.toFetch)
    if c.debug:
        print("   Filtered out " + str(len(retrievedURLs) - len(toLeft)) + " urls") 
    return toLeft
    
#-------------------------------------------------------------------------  
# Store HTML pages (DONE)  
def storePage(c, htmlData):
    
    relBeginIndex = len(c.rootPage)
    totalPath = "./" + c.example + "/pages/" + c.toFetch[relBeginIndex + 1:]
    
    if c.debug:
        print("   Saving HTML page " + totalPath + "...")
    
    totalDir = os.path.dirname(totalPath)
    
    if not os.path.exists(totalDir):
        os.makedirs(totalDir)
        
    with open(totalPath, "wb+") as f:
        f.write(htmlData)
        f.close()
        
#-------------------------------------------------------------------------  
# Store URLs (DONE)  
def storeURLs(c):
    relBeginIndex = len(c.rootPage)
    totalPath = "./" + c.example + "/urls/urls.txt"
    
    if c.debug:
        print("Saving URLs " + totalPath + "...")
    
    totalDir = os.path.dirname(totalPath)
    
    if not os.path.exists(totalDir):
        os.makedirs(totalDir)
        
    data = [url for url in c.URLs]
    data.sort()
        
    with open(totalPath, "w+") as f:
        for line in data:
            f.write(line + "\n")
        f.close()
        
   
#-------------------------------------------------------------------------  
# Update outgoing links (DONE)  
def updateOutgoingURLs(c, retrievedURLsWD):
    if c.toFetch not in c.outgoingURLs:
        c.outgoingURLs[c.toFetch] = set([])
    for url in retrievedURLsWD:
        c.outgoingURLs[c.toFetch].add(url)
        
#-------------------------------------------------------------------------  
# Update incoming links (DONE)  
def updateIncomingURLs(c, retrievedURLsWD):
    for url in retrievedURLsWD:
        if url not in c.incomingURLs:
            c.incomingURLs[url] = set([])
        c.incomingURLs[url].add(c.toFetch)
    
#-------------------------------------------------------------------------  
# Store outgoing URLs (DONE)  
def storeOutgoingURLs(c):
    relBeginIndex = len(c.rootPage)
    totalPath = "./" + c.example + "/outgoing_urls/outgoing_urls.txt"
    
    if c.debug:
        print("Saving URLs " + totalPath + "...")
    
    totalDir = os.path.dirname(totalPath)
    
    if not os.path.exists(totalDir):
        os.makedirs(totalDir)
        
    data = [url for url in c.outgoingURLs]
    data.sort()
        
    with open(totalPath, "w+") as f:
        for line in data:
            s = list(c.outgoingURLs[line])
            s.sort()
            for l in s:
                f.write(line + " " + l + "\n")
        f.close()
        

#-------------------------------------------------------------------------  
# Store incoming URLs (DONE)  
def storeIncomingURLs(c):
    relBeginIndex = len(c.rootPage)
    totalPath = "./" + c.example + "/incoming_urls/incoming_urls.txt"
    
    if c.debug:
        print("Saving URLs " + totalPath + "...")
    
    totalDir = os.path.dirname(totalPath)
    
    if not os.path.exists(totalDir):
        os.makedirs(totalDir)
        
    data = [url for url in c.incomingURLs]
    data.sort()
        
    with open(totalPath, "w+") as f:
        for line in data:
            s = list(c.incomingURLs[line])
            s.sort()
            for l in s:
                f.write(line + " " + l + "\n")
        f.close()
        


if __name__ == "__main__":
    main()
