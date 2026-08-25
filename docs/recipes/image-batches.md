# Convert image batches

## JPEG conversion

```bash
pyffmpegcore images convert --input-dir source-images --output-dir jpeg-images --format jpg --quality 85
```

## Web optimization

```bash
pyffmpegcore images optimize --input-dir source-images --output-dir optimized-images --max-width 1920 --max-height 1080 --quality 85
```

## WebP conversion

```powershell
pyffmpegcore images webp --input-dir "source images" --output-dir "webp images" --quality 80
```

The current image commands report partial success with exit code `6`. A nonempty output directory is refused unless `--force` is explicit. Keep the input directory separate from the output directory to prevent accidental recursive work.
