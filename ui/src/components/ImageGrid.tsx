import Grid from '@mui/material/Grid2';
import React from "react";
import ArtItemCard from "./ArtItemCard";
import Image from "../models/Image";

export interface ImageGridProps {
    items: Image[];
}

function ImageGrid({items}: ImageGridProps) {
    return (
        <Grid container spacing={{xs: 2, md: 3}} columns={{xs: 4, sm: 8, md: 12}}>
            {items.map((_, index) => (
                <Grid key={index} size={{xs: 4, sm: 2, md: 2}}>
                    <ArtItemCard item={items[index]}/>
                </Grid>
            ))}
        </Grid>)
}

export default ImageGrid;