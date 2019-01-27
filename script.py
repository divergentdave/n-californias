#!/usr/bin/env python3
import collections
import datetime
import io
import math
import os
import pickle
import random
import sys

from mastodon import Mastodon
import matplotlib as mpl
from num2words import num2words

mpl.use("agg")

import osmnx as ox  # noqa: E402
import seaborn  # noqa: E402

CLIENT_CRED_SECRET_FILENAME = "pytooter_clientcred.secret"
COUNTIES_FILENAME = "counties.pickle"
PROJECTED_FILENAME = "projected.pickle"
NEIGHBORS_FILENAME = "neighbors.pickle"
COUNTIES = [
    "Alameda",
    "Alpine",
    "Amador",
    "Butte",
    "Calaveras",
    "Colusa",
    "Contra Costa",
    "Del Norte",
    "El Dorado",
    "Fresno",
    "Glenn",
    "Humboldt",
    "Imperial",
    "Inyo",
    "Kern",
    "Kings",
    "Lake",
    "Lassen",
    "Los Angeles",
    "Madera",
    "Marin",
    "Mariposa",
    "Mendocino",
    "Merced",
    "Modoc",
    "Mono",
    "Monterey",
    "Napa",
    "Nevada",
    "Orange",
    "Placer",
    "Plumas",
    "Riverside",
    "Sacramento",
    "San Benito",
    "San Bernardino",
    "San Diego",
    "San Francisco",
    "San Joaquin",
    "San Luis Obispo",
    "San Mateo",
    "Santa Barbara",
    "Santa Clara",
    "Santa Cruz",
    "Shasta",
    "Sierra",
    "Siskiyou",
    "Solano",
    "Sonoma",
    "Stanislaus",
    "Sutter",
    "Tehama",
    "Trinity",
    "Tulare",
    "Tuolumne",
    "Ventura",
    "Yolo",
    "Yuba"
]
assert len(COUNTIES) == 58

Media = collections.namedtuple("Media", ["buf", "mimetype", "description"])


def fetch_counties_gdf():
    names = ["{} County, California, USA".format(county)
             for county in COUNTIES]
    result = ox.gdf_from_places(names, gdf_name="counties")
    return result


def compute_neighbors(l):
    neighbors = collections.defaultdict(list)
    for i in range(len(l)):
        for j in range(i):
            dist = l[i].distance(l[j])
            if dist < 0.001:
                neighbors[i].append(j)
                neighbors[j].append(i)
    return dict(neighbors)


def cache_result(path, func, *args, **kwargs):
    if os.path.isfile(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    else:
        result = func(*args, **kwargs)
        with open(path, "wb") as f:
            pickle.dump(result, f)
        return result


def log_in(server, username, password):
    mastodon = Mastodon(
        client_id=CLIENT_CRED_SECRET_FILENAME,
        api_base_url=server
    )
    mastodon.log_in(username, password)
    return mastodon


def make_post(mastodon, text, media_in):
    media_dicts = []
    for media in media_in:
        media_dict = mastodon.media_post(media.buf, media.mimetype,
                                         media.description)
        media_dicts.append(media_dict)
    mastodon.status_post(
        text,
        media_ids=media_dicts,
        language="en"
    )


def holiday_colors():
    today = datetime.date.today()
    holidays = [
        (datetime.date(today.year, 2, 14), ("red", "pink")),
        (datetime.date(today.year, 3, 17), ("green",)),
        (datetime.date(today.year, 7, 4), ("red", "white", "blue")),
        (datetime.date(today.year, 10, 31), ("black", "orange")),
        (datetime.date(today.year, 12, 25), ("red", "green")),
    ]
    week = datetime.timedelta(weeks=1)
    for holiday_date, holiday_color_kws in holidays:
        if holiday_date - week < today and today <= holiday_date:
            return ([rgb for name, rgb in seaborn.xkcd_rgb.items()
                     if any(kw in name.lower() for kw in holiday_color_kws)],
                    holiday_color_kws)
    return list(seaborn.xkcd_rgb.values()), None


def make_map(n_californias, all_colors, color_keywords):
    counties = cache_result(COUNTIES_FILENAME, fetch_counties_gdf)
    projected = cache_result(PROJECTED_FILENAME, ox.project_gdf, counties)
    geom_list = list(counties.itertuples())
    geom_list = counties["geometry"].tolist()
    neighbors = cache_result(NEIGHBORS_FILENAME, compute_neighbors, geom_list)

    n_californias = min(n_californias, len(COUNTIES))
    n_californias = min(n_californias, len(all_colors))

    remaining = set(range(len(geom_list)))
    californias = []
    for _ in range(n_californias):
        temp = random.choice(list(remaining))
        remaining.remove(temp)
        californias.append([temp])
    while remaining:
        which_california = random.randrange(n_californias)
        new_neighbor_choices = set()
        for county_id in californias[which_california]:
            for neighbor_id in neighbors[county_id]:
                if neighbor_id in remaining:
                    new_neighbor_choices.add(neighbor_id)
        if not new_neighbor_choices:
            continue
        new_neighbor = random.choice(list(new_neighbor_choices))
        californias[which_california].append(new_neighbor)
        remaining.remove(new_neighbor)

    face_colors = [None] * len(geom_list)
    palette = random.sample(all_colors, n_californias)
    for color, california in zip(palette, californias):
        for county_id in california:
            face_colors[county_id] = color

    fig, ax = ox.plot_shape(projected, fc=face_colors)
    bio = io.BytesIO()
    fig.savefig(bio)
    bio.seek(0)

    number_word = num2words(n_californias)
    text = "{} Californias".format(number_word[:1].upper() + number_word[1:])
    if color_keywords is None:
        description = ("A map of California, where the counties are {} "
                       "different colors".format(n_californias))
    else:
        if len(color_keywords) == 1:
            kws_joined = color_keywords[0]
        elif len(color_keywords) == 2:
            kws_joined = " and ".join(color_keywords)
        else:
            kws_joined = "{}, and {}".format(", ".join(color_keywords[:-1]),
                                             color_keywords[-1])
        description = ("A map of California, where the counties are {} "
                       "different shades of {}".format(n_californias,
                                                       kws_joined))

    return text, bio, description


def main():
    args = sys.argv[1:]
    dry_run = ("--dry-run" in args or "-d" in args)

    if "--help" in args or "-h" in args:
        print("Usage: Run with no arguments to post a status. Pass --dry-run "
              "or -d as a command line argument to create a map, but not post "
              "it.")
        print()
        print("The environment variables MASTODON_SERVER, MASTODON_USERNAME, "
              "and MASTODON_PASSWORD must be set with account credentials "
              "to post a status.")
        sys.exit(0)

    if not dry_run:
        if not os.path.isfile(CLIENT_CRED_SECRET_FILENAME):
            print("Error: {} does not exist, run Mastodon.create_app manually "
                  "first".format(CLIENT_CRED_SECRET_FILENAME), file=sys.stderr)
            sys.exit(1)
        server = os.environ.get("MASTODON_SERVER")
        if server is None:
            print("Error: Set the environment variable MASTODON_SERVER to the "
                  "URL of the Mastodon server", file=sys.stderr)
            sys.exit(1)
        username = os.environ.get("MASTODON_USERNAME")
        if username is None:
            print("Error: Set the environment variable MASTODON_USERNAME to "
                  "your username or email", file=sys.stderr)
            sys.exit(1)
        password = os.environ.get("MASTODON_PASSWORD")
        if password is None:
            print("Error: Set the environment variable MASTODON_PASSWORD to "
                  "your password", file=sys.stderr)
            sys.exit(1)

    all_colors, color_keywords = holiday_colors()
    max_n_californias = min(len(COUNTIES), len(all_colors))
    n_californias = int(math.floor(random.triangular(2, max_n_californias + 1,
                                                     2)))
    text, img_data, description = make_map(n_californias, all_colors,
                                           color_keywords)

    if dry_run:
        print("Text: {!r}".format(text))
        print("Image description: {!r}".format(description))
        with open("image.png", "wb") as f:
            f.write(img_data.read())
        print("Map saved to image.png")
    else:
        mastodon = log_in(server, username, password)
        make_post(mastodon, text, [Media(img_data, "image/png", description)])


if __name__ == "__main__":
    main()
