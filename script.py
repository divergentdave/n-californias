#!/usr/bin/env python3
import collections
import io
import os
import pickle
import random

from mastodon import Mastodon
import matplotlib as mpl
from num2words import num2words

mpl.use("agg")

import osmnx as ox  # noqa: E402
import seaborn  # noqa: E402

MASTODON_SERVER = os.environ["MASTODON_SERVER"]
MASTODON_USERNAME = os.environ["MASTODON_USERNAME"]
MASTODON_PASSWORD = os.environ["MASTODON_PASSWORD"]
COUNTIES_FILENAME = "counties.pickle"
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


def log_in():
    mastodon = Mastodon(
        client_id="pytooter_clientcred.secret",
        api_base_url=MASTODON_SERVER
    )
    mastodon.log_in(
        MASTODON_USERNAME,
        MASTODON_PASSWORD
    )
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


def main():
    counties = cache_result(COUNTIES_FILENAME, fetch_counties_gdf)
    geom_list = list(counties.itertuples())
    geom_list = counties["geometry"].tolist()
    neighbors = cache_result(NEIGHBORS_FILENAME, compute_neighbors, geom_list)

    n_californias = random.randint(2, 20)
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

    projected = ox.project_gdf(counties)
    face_colors = [None] * len(geom_list)
    palette = random.sample(list(seaborn.xkcd_rgb.values()), n_californias)
    for color, california in zip(palette, californias):
        for county_id in california:
            face_colors[county_id] = color

    fig, ax = ox.plot_shape(projected, fc=face_colors)
    bio = io.BytesIO()
    fig.savefig(bio)
    bio.seek(0)

    number_word = num2words(n_californias)
    text = "{} Californias".format(number_word[:1].upper() + number_word[1:])
    description = ("A map of California, where the counties are {} different "
                   "colors".format(n_californias))

    mastodon = log_in()
    make_post(mastodon, text, [Media(bio, "image/png", description)])


if __name__ == "__main__":
    main()
