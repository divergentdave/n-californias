#!/usr/bin/env python3
import collections
import os
import pickle
import random

from num2words import num2words
import osmnx as ox

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
    for california in californias:
        color = "#{:02x}{:02x}{:02x}".format(random.randint(0x60, 0xe0),
                                             random.randint(0x60, 0xe0),
                                             random.randint(0x60, 0xe0))
        for county_id in california:
            face_colors[county_id] = color

    number_word = num2words(n_californias)
    print("{} Californias".format(number_word[:1].upper() + number_word[1:]))

    fig, ax = ox.plot_shape(projected, fc=face_colors)
    fig.savefig("map.png")


if __name__ == "__main__":
    main()
