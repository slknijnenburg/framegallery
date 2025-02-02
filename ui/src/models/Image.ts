export default interface Image {
  id: number;
  filename: string;
  filepath: string;
  filetype: string;
  thumbnail_path: string;
  width: number;
  height: number;
  aspect_width: number;
  aspect_height: number;
  matte_id?: string;
}
