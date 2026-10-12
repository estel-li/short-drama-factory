"""Rebuild a complete editing version without text API or GPU calls."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.finishing import build
from app.storage import contained,digest,read_json


def main():
    parser=argparse.ArgumentParser(description='从冻结原片、字幕与剪辑配方重建成片，不调用 GPU。')
    parser.add_argument('--project',required=True,type=Path)
    parser.add_argument('--recipe',required=True,help='相对项目目录，如 edits/<版本>/recipe.json')
    args=parser.parse_args();project=args.project.resolve();path=contained(project,args.recipe)
    if path.name!='recipe.json' or not (path.parent/'completed.json').is_file():raise ValueError('需要已完成版本的 recipe.json。')
    recipe=read_json(path)
    if digest(recipe)!=read_json(path.parent/'媒体验收.json')['recipe_hash']:raise ValueError('原配方已改变，不能作为冻结版本重建。')
    output=build(project,recipe['story'],[],recipe['width'],recipe['height'],recipe['settings'],print,recipe=recipe)
    print(output)


if __name__=='__main__':main()
