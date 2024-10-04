interface ArtItem {
    content_id: string;
    local_filename?: string;
    category_id: string;
    slideshow: boolean;
    matte_id: string;
    portrait_matte_id: string;
    width: number;
    height: number;
    image_date: string;
    content_type: string;
    thumbnail_filename?: string;
    thumbnail_filetype?: string;
    thumbnail_data?: string;
}

export default ArtItem;