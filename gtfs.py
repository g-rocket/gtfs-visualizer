#!/usr/bin/env python3

import argparse
import io
import os
import zipfile
import subprocess

import PIL.Image, PIL.ImageDraw

def main():
    p = argparse.ArgumentParser()

    p.add_argument('gtfs', type=os.path.realpath, nargs='+', help='Path to gtfs directory')
    p.add_argument('output', help='Image file to save')
    p.add_argument('--list-routes', action='store_true', help='List routes (by color)')
    p.add_argument('--exclude', nargs='+', help='List of routes/colors to exclude', default=[])
    p.add_argument('--exclude-nocolor', action='store_true')
    p.add_argument('--maxdim', '--width', type=int, default=1000)
    p.add_argument('--color', action='store_true')
    p.add_argument('--open', action='store_true')

    args = p.parse_args()

    colors = []
    if not args.color:
        colors = [{}] * len(gtfs)

    bounding_box = None
    for gtfs in args.gtfs:
        if args.color:
            colors.append(get_colors(gtfs, args))
        bounding_box = get_bounding_box(gtfs, colors[-1], args.exclude_nocolor, bounding_box)

    image = make_image(args.maxdim, bounding_box)

    for gtfs, color in zip(args.gtfs, colors):
        draw_gtfs(gtfs, bounding_box, image, color, args)

    image.save(args.output)

    if args.open:
        subprocess.Popen(['feh', args.output])

def get_colors(gtfs, args):
    with open_file(gtfs, 'routes.txt') as routes:
        route_colors = {}
        headers = parse_headers(routes.readline())
        if 'route_id' not in headers or 'route_color' not in headers:
            return {}
        for line in routes:
            items = splitline(line)
            color_str = items[-(len(headers) - headers['route_color'])]
            if len(color_str) == 6 and all(c in '0123456789abcdefABCDEF' for c in color_str):
                route_colors[items[headers['route_id']]] = color_str
            else:
                if color_str:
                    print(f'WARNING: unknown color {color_str}')
                # TODO: maybe configurable fallback?
                route_colors[items[headers['route_id']]] = '000000'
    if args.list_routes:
        reversed_colors = {}
        for id, color in route_colors.items():
            if color not in reversed_colors:
                reversed_colors[color] = []
            reversed_colors[color].append(id)
        print(reversed_colors)
    shape_colors = {}
    with open_file(gtfs, 'trips.txt') as trips:
        headers = parse_headers(trips.readline())
        if 'route_id' not in headers or 'shape_id' not in headers:
            return {}
        for line in trips:
            items = splitline(line)
            route_id = items[headers['route_id']]
            if False or route_id in args.exclude:
                # Make it transparent
                shape_colors[route_id] = 'exclude'
            elif route_id in route_colors:
                if route_colors[route_id] in args.exclude:
                    shape_colors[route_id] = 'exclude'
                else:
                    shape_colors[items[headers['shape_id']]] = '#' + route_colors[route_id]
    return shape_colors

def splitline(line):
    return [stripquote(item.rstrip(' ')) for item in line.rstrip('\n').split(',')]

def parse_headers(line):
    if line[0] in ('\ufeff', '\ufffe'):
        line = line[1:]
    return {item: idx for idx,item in enumerate(splitline(line))}

def parse_shapes_offsets(headers_line):
    headers = parse_headers(headers_line)
    return headers['shape_id'], headers['shape_pt_lat'], headers['shape_pt_lon']

def parse_shape_line(line, offsets):
    parts = splitline(line)
    # ID, lon, -lat
    # TODO: this is an odd ordering to make x,y work...
    return parts[offsets[0]], float(stripquote(parts[offsets[2]])), -float(stripquote(parts[offsets[1]]))

def stripquote(item):
    if item and item[0] == '"' and item[-1] == '"':
        return item[1:-1]
    else:
        return item

def get_bounding_box(gtfs, colors, exclude_nocolor, bounding_box):
    with open_file(gtfs, 'shapes.txt') as shapefile:
        offsets = parse_shapes_offsets(shapefile.readline())
        if bounding_box is not None:
            minlat = bounding_box[0]
            maxlat = bounding_box[1]
            minlon = bounding_box[2]
            maxlon = bounding_box[3]
        else:
            _, lat, lon = parse_shape_line(shapefile.readline(), offsets)
            minlat = lat
            maxlat = lat
            minlon = lon
            maxlon = lon
        for line in shapefile:
            id, lat, lon = parse_shape_line(line, offsets)
            if colors.get(id, 'exclude' if exclude_nocolor else '') == 'exclude':
                continue
            if lat < minlat:
                minlat = lat
            if lat > maxlat:
                maxlat = lat
            if lon < minlon:
                minlon = lon
            if lon > maxlon:
                maxlon = lon
    return (minlat, maxlat, minlon, maxlon)

def make_image(maxdim, bounding_box):
    minlat = bounding_box[0]
    maxlat = bounding_box[1]
    minlon = bounding_box[2]
    maxlon = bounding_box[3]

    width = maxdim
    height = int((width-10) * (maxlon - minlon) / (maxlat - minlat))+10

    if height > width:
        height = maxdim
        width = int((height-10) * (maxlat - minlat) / (maxlon - minlon))+10

    image = PIL.Image.new('RGB', (width, height), color=(255,255,255))

    return image

def draw_gtfs(gtfs, bounding_box, image, colors, args):
    minlat = bounding_box[0]
    maxlat = bounding_box[1]
    minlon = bounding_box[2]
    maxlon = bounding_box[3]
    with open_file(gtfs, 'shapes.txt') as shapefile:
        draw = PIL.ImageDraw.Draw(image)
        lastid = None
        px = None
        py = None
        offsets = parse_shapes_offsets(shapefile.readline())
        for line in shapefile:
            id, lat, lon = parse_shape_line(line, offsets)
            if args.list_routes and (lat in (minlat,maxlat) or lon in (minlon,maxlon)):
                print(id, colors.get(id))
            if colors.get(id, 'exclude' if args.exclude_nocolor else None) == 'exclude':
                continue
            x = int((lat - minlat) * (image.width-10) / (maxlat - minlat))+5
            y = int((lon - minlon) * (image.height-10) / (maxlon - minlon))+5
            if id == lastid:
                draw.line((px, py, x, y), fill=colors.get(id, '#000000'))
            px = x
            py = y
            lastid = id

def open_file(gtfs, name):
    if os.path.isdir(gtfs):
        return open(os.path.join(gtfs, name), encoding='utf-8')
    elif zipfile.is_zipfile(gtfs):
        return io.TextIOWrapper(zipfile.ZipFile(gtfs).open(name), encoding='utf-8')

if __name__ == '__main__':
    main()

