import subprocess
import os
import argparse
import bwtex

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("inputfolder",
                        help="Path to folder with textures.")
    parser.add_argument('--topng',
                        action='store_true')
    parser.add_argument('--tobw',
                        action='store_true')
    parser.add_argument('--bw1',
                        action='store_true')
    parser.add_argument('--bw2',
                        action='store_true')
    parser.add_argument("outputfolder", default=None, nargs = '?',
                        help=("Path to output folder. Default is same folder as input.") )

    args = parser.parse_args()
    
    currdir = os.path.dirname("__file__")
    
    assert args.bw1 is not args.bw2 
    assert args.tobw is not args.topng 
    
    game = "--bw1" if args.bw1 else "--bw2"
    
    outputfolder = args.outputfolder
    if outputfolder is None:
        outputfolder = args.inputfolder
    
    for fname in os.listdir(args.inputfolder):
        if args.tobw:
            if fname.endswith(".png"):
                texname = fname.split(".")[0]
                print("Converting", os.path.join(args.inputfolder, fname))
                result = subprocess.call(["python",  
                    os.path.join(currdir, "conv.py"), 
                    game,
                    os.path.join(args.inputfolder, fname),
                    os.path.join(outputfolder, texname+".texture")])
                
                print("Saved to", os.path.join(outputfolder, texname+".texture"))
        else:
            if fname.endswith(".texture"):
                print("Converting", os.path.join(args.inputfolder, fname))
                with open(os.path.join(args.inputfolder, fname), "rb") as f:
                    if args.bw1:
                        tex = bwtex.BW1Texture.from_file(f)
                    else:
                        tex = bwtex.BW2Texture.from_file(f)
                settings = tex.header_to_string()
                tex.mipmaps[0].save(os.path.join(outputfolder, fname.replace(".texture", "")+"."+tex.fmt+"."+settings+".png"))
                print("Saved to", os.path.join(outputfolder, fname.replace(".texture", "")+"."+tex.fmt+"."+settings+".png"))