import sys
import requests
import datetime as dt
import time
import json
import numpy as np
import matplotlib.pyplot as plt
from dateutil.parser import parse
sys.path.append('ergo-master')
from ergo import Metaculus
from bs4 import BeautifulSoup as bs


# Misc functions
def move_urls(soup):
    links = soup.find_all('a')
    for link in links:
        try:
            link.string = link.string + ' (' + link['href'] + ') '
        except:
            print(link)
    return soup

def ftime(t):
    if type(t) == str:
        return f'{t[:10]}, {t[11:16]}'
    return t.strftime("%m-%d-%Y, %H:%M")

def print_comment(comment, max_date):
    if parse(comment['created_time']) < max_date:
        t = comment["created_time"]
        print(f'{comment["author_name"]}   {ftime(comment["created_time"])}')
        print(comment["comment_text"])
        print()
        return True
    return False

def practical_score(
    probability: float,
    max_probability: float = 0.99,
    max_score: float = 2,
) -> float:
    """Calculate the practical score for the provided probability.
    Parameters
    ----------
    probability
        A number greater than 0 and less than or equal to `max_probability`.
    max_probability
        The maximum probability allowed. Defaults to 0.9999.
    max_score
        The maximum score allowed. Defaults to 2.
    Returns
    """
    nominator = max_score * (np.log2(probability) + 1)
    denominator = np.log2(max_probability + 1)
    score = nominator / denominator
    if score > max_score:
        return max_score
    return score





#   Extend Metaculus class
class MyMetaculus(Metaculus):
    def __init__(self):
        self.predictions = []
        self.score = 0
        super().__init__()

    def save_comments(self, offset='0'):
        t = time.time()
        url = f"{self.api_url}/comments/?limit=1000&offset=" + offset
        with open('comments.json', 'a') as outfile:
            while url is not None:
                r = self.s.get(url)
                if r.status_code == 503:
                    time.sleep(5)
                    continue
                print(r)
                data = r.json()
                outfile.write(',')
                json.dump(data, outfile)
                url = data['next']

                print('TIME',time.time()-t)
                print('next url',url)
        
        print('DONE')
    
    def read_comments(self):
        with open('comments.json', 'r') as infile:
            text = infile.read() + "]}"
            j = json.loads(text)
        self.comments = j
        print(j['l'][-1]['results'][-1])

    def structure_comments(self):
        t = time.time()
        questions = {}
        with open('comments/comments.json', 'r') as infile:
            text = infile.read() + "]}"
            j = json.loads(text)
            for comments in j['l']:
                for comment in comments['results']:
                    question_id = comment['question']['id']
                    k = (question_id // 1000) * 1000
                    if k not in questions:
                        questions[k] = {}
                    if question_id not in questions[k]:
                        questions[k][question_id] = [comment]
                    else:
                        for c in questions[k][question_id]:
                            if comment['id'] == c['id']:
                                # print(f"{c['id']} is a duplicate")
                                break
                            elif comment['parent'] == c['id']:
                                # print(f"{comment['id']} is {c['id']}'s child")
                                if 'children' in c:
                                    for child in c['children']:
                                        if comment['id'] == child['id']:
                                            # print(f"{child['id']} is a duplicate")
                                            break
                                    else:
                                        c['children'].append(comment)
                                else:
                                   c['children'] = [comment]
                                break
                        else:
                            questions[k][question_id] += [comment]
                # print('q id', question_id, 'time', time.time()-t)

        for k,k_block in questions.items():
            with open(f'comments/{str(k)}.json', 'w') as outfile:
                json.dump(k_block, outfile)


    def show_binary(self):
        qs = self.get_questions('resolved')

        for q in qs:
            if q.possibilities['type'] == 'binary':
                self.q = q
                break


        ##  Scrape website

        url = 'https://www.metaculus.com' + q.page_url
        page = requests.get(url)
        soup = bs(page.content, 'html.parser')

        ### Get description
        content = soup.find(class_='question__content')
        move_urls(content)

        print()
        print(q.title)
        print(ftime(q.created_time))
        print()
        print(content.get_text())
        print()

        ## Get comments
        max_date = parse('Dec 10, 2020 at 00:00:00 UTC')

        k = (q.id // 1000) * 1000
        with open(f'comments/{str(k)}.json', 'r') as infile:
            text = infile.read()
        comments = json.loads(text)[str(q.id)]


        print('--------------------------')
        print()
        for comment in comments:
            # d = max_date
            # if d.tzinfo is not None and d.tzinfo.utcoffset(d) is not None:
            #     print('max date is aware')
            # d = parse(comment['created_time'])
            # if d.tzinfo is not None and d.tzinfo.utcoffset(d) is not None:
            #     print('created time is aware')
            printed = print_comment(comment, max_date)
            if printed and 'children' in comment:
                for child in comment['children']:
                    print_comment(child, max_date)
            if printed:
                print('--------------------------')
                print()
    
    def predictq(self, prediction):
        p = prediction if self.q.resolution else 1-prediction
        score = practical_score(p, 0.99, 2)
        print('The answer is', bool(self.q.resolution))
        print('Score:', score)
        self.score += score
        self.predictions.append((self.q, prediction, score))
    
    def eval_predictions(self):
        print('Score so far:', self.score)
        # Calibration chart
        xs = np.concatenate((np.arange(0.50,0.95,0.1), [.975]))
        ys = [[] for _ in xs]
        for q,p,_ in self.predictions:
            for i,x in enumerate(xs):
                if x+.05 >= p > 0.5:
                    ys[i].append(q.resolution)
                    break
                if x+.05 > 1-p >= 0.5:
                    ys[i].append(1-q.resolution)
                    break
        plt.plot(xs, [sum(y)/len(y) if len(y)>0 else None for y in ys])




m = MyMetaculus()

# mm.save_comments('41000')
# mm.structure_comments()
# mm.read_comments()
# exit()


