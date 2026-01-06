import argparse
import cv2
import glob
import matplotlib
import numpy as np
import os
import torch

from depth_anything_v2.dpt import DepthAnythingV2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Depth Anything V2')
    
    parser.add_argument('--img-path', type=str)
    parser.add_argument('--input-size', type=int, default=518)
    parser.add_argument('--outdir', type=str, default='./vis_depth')
    
    parser.add_argument('--encoder', type=str, default='vitl', choices=['vits', 'vitb', 'vitl', 'vitg'])
    
    parser.add_argument('--pred-only', dest='pred_only', action='store_true', help='only display the prediction')
    parser.add_argument('--grayscale', dest='grayscale', action='store_true', help='do not apply colorful palette')
    parser.add_argument('--save-raw', dest='save_raw', action='store_true', help='save raw depth map as .raw file for YUV player')
    parser.add_argument('--save-float', dest='save_float', action='store_true', help='save float depth values as .bin file')
    
    args = parser.parse_args()
    
    DEVICE = 'cuda' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu'
    
    model_configs = {
        'vits': {'encoder': 'vits', 'features': 64, 'out_channels': [48, 96, 192, 384]},
        'vitb': {'encoder': 'vitb', 'features': 128, 'out_channels': [96, 192, 384, 768]},
        'vitl': {'encoder': 'vitl', 'features': 256, 'out_channels': [256, 512, 1024, 1024]},
        'vitg': {'encoder': 'vitg', 'features': 384, 'out_channels': [1536, 1536, 1536, 1536]}
    }
    
    depth_anything = DepthAnythingV2(**model_configs[args.encoder])
    depth_anything.load_state_dict(torch.load(f'checkpoints/depth_anything_v2_{args.encoder}.pth', map_location='cpu'))
    depth_anything = depth_anything.to(DEVICE).eval()
    
    if os.path.isfile(args.img_path):
        if args.img_path.endswith('txt'):
            with open(args.img_path, 'r') as f:
                filenames = f.read().splitlines()
        else:
            filenames = [args.img_path]
    else:
        filenames = glob.glob(os.path.join(args.img_path, '**/*'), recursive=True)
    
    os.makedirs(args.outdir, exist_ok=True)
    
    cmap = matplotlib.colormaps.get_cmap('Spectral_r')
    
    for k, filename in enumerate(filenames):
        print(f'Progress {k+1}/{len(filenames)}: {filename}')
        
        raw_image = cv2.imread(filename)
        
        depth = depth_anything.infer_image(raw_image, args.input_size)
        
        # Get base filename for saving
        base_filename = os.path.splitext(os.path.basename(filename))[0]
        
        # Save raw float depth values if requested
        if args.save_float:
            float_path = os.path.join(args.outdir, base_filename + '_float.bin')
            depth.astype(np.float32).tofile(float_path)
            print(f'  Saved float depth to: {float_path}')
            print(f'  Shape: {depth.shape}, Min: {depth.min():.4f}, Max: {depth.max():.4f}')
        
        # Normalize depth to 0-255
        depth_normalized = (depth - depth.min()) / (depth.max() - depth.min()) * 255.0
        depth_uint8 = depth_normalized.astype(np.uint8)
        
        # Save raw 8-bit depth map for YUV player if requested
        if args.save_raw:
            raw_path = os.path.join(args.outdir, base_filename + '.raw')
            depth_uint8.tofile(raw_path)
            print(f'  Saved raw depth to: {raw_path}')
            print(f'  YUVPlayer config: {depth.shape[1]}x{depth.shape[0]}, Y800 (8-bit grayscale)')
        
        # Prepare visualization
        if args.grayscale:
            depth_vis = np.repeat(depth_uint8[..., np.newaxis], 3, axis=-1)
        else:
            depth_vis = (cmap(depth_uint8)[:, :, :3] * 255)[:, :, ::-1].astype(np.uint8)
        
        if args.pred_only:
            cv2.imwrite(os.path.join(args.outdir, base_filename + '.png'), depth_vis)
        else:
            split_region = np.ones((raw_image.shape[0], 50, 3), dtype=np.uint8) * 255
            combined_result = cv2.hconcat([raw_image, split_region, depth_vis])
            
            cv2.imwrite(os.path.join(args.outdir, base_filename + '.png'), combined_result)