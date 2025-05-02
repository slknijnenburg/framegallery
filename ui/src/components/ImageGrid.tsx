import Grid from '@mui/material/Grid2';
import React, { useCallback, useState, useEffect } from 'react';
import ArtItemCard from './ArtItemCard';
import Image from '../models/Image';
import { Chip, CircularProgress, Divider } from '@mui/material';
import Container from '@mui/material/Container';

export interface ImageGridProps {
  items: Image[];
}

function ImageGrid({ items }: ImageGridProps) {
  const [visibleCount, setVisibleCount] = useState(18);
  const [loading, setLoading] = useState(false);
  const [allImagesDisplayed, setAllImagesDisplayed] = useState(false);

  useEffect(() => {
    setAllImagesDisplayed(visibleCount >= items.length);
  }, [items.length, visibleCount]);

  const loadMore = useCallback(() => {
    setLoading(true);
    setVisibleCount((visibleCount) => {
      const newVisibleCount = visibleCount + 6;

      if (newVisibleCount >= items.length) {
        setAllImagesDisplayed(newVisibleCount >= items.length);
      }

      return newVisibleCount;
    });
    setLoading(false);
  }, [items.length]);

  const handleScroll = useCallback(() => {
    if (window.innerHeight + document.documentElement.scrollTop !== document.documentElement.offsetHeight) {
      return;
    }

    if (allImagesDisplayed || loading) {
      return;
    }

    loadMore();
  }, [allImagesDisplayed, loading, loadMore]);

  useEffect(() => {
    window.addEventListener('scroll', handleScroll);
    setAllImagesDisplayed(visibleCount >= items.length);
    return () => window.removeEventListener('scroll', handleScroll);
  }, [handleScroll, items.length, visibleCount]);

  return (
    <>
      <Grid container spacing={{ xs: 2, md: 3 }} columns={{ xs: 4, sm: 8, md: 12 }}>
        {items.slice(0, visibleCount).map((item, index) => (
          <Grid key={index} size={{ xs: 4, sm: 2, md: 2 }}>
            <ArtItemCard item={item} />
          </Grid>
        ))}
      </Grid>
      {!allImagesDisplayed && (
        <Container sx={{ py: 5, mx: 'auto' }}>
          <Divider>
            <Chip label="Load more images" size="small" onClick={loadMore} />
          </Divider>
        </Container>
      )}
      {loading && (
        <Container sx={{ py: 5, mx: 'auto' }}>
          <Divider>
            <CircularProgress />
          </Divider>
        </Container>
      )}
      {allImagesDisplayed && (
        <Container sx={{ py: 5, mx: 'auto' }}>
          <Divider>
            <Chip label="All images are displayed" size="small" />
          </Divider>
        </Container>
      )}
    </>
  );
}

export default ImageGrid;
