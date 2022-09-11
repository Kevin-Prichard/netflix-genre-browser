# netflix-genre-browser
A simple Python requests crawler for finding Netflix genre page crawler. Produces a Sqlite database.

## Installation
```shell
$ git clone git@github.com:Kevin-Prichard/netflix-genre-browser.git
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements
```

## Execution
By default crawler.py uses requests_cache, for speeding up dev iterations.  To disable, change MODE to something other than "dev", like "prod".
```shell
$ ./crawler.py
```

## Database
Produces a Sqlite database named 'netflix_genres.sqlite'.  Tables are:
```text
genre
    id INT PRIMARY KEY
    name VARCHAR(128)
    synopsis VARCHAR(255)
    created DATETIME
    updated DATETIME

title
    id INT PRIMARY KEY
    name VARCHAR(128)
    img_src VARCHAR(255)
    last DATETIME

genre_title  # provides tertiary link btw genre and title
    genre_id INT
    title_id INT
    last DATETIME
    PRIMARY KEY(genre_id, title_id)

genre_history
    id INT PRIMARY KEY
    status INT
    last DATETIME
```

## Results
Count of titles by genre:
```sqlite
select g.id, g.name, count(t.name)
from genre g 
    join genre_title gt on gt.genre_id=g.id
    join title t on t.id=gt.title_id
group by g.id
order by g.name;
```

Show all titles under a genre ID:

```sqlite
select *
from title t
join genre_title gt on gt.title_id=t.id
where gt.genre_id=11559
order by t.name;
```

## To-Dos
- It's unclear whether Netflix is responding to my requests with correct answers.  It would be unsurprising to learn that for a noise IP, instead of rate-limiting, they redirect to login on otherwise valid requests to existing genre pages.

With that in mind, I looked up some existing lists of Netflix genre codes, to compare.  There are big gaps, in my captured results.
