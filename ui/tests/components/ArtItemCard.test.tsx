import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import ArtItemCard from '../../src/components/ArtItemCard';
import type Image from '../../src/models/Image';
import { jest, expect, it, describe } from '@jest/globals';
import axios from 'axios';

describe('ArtItemCard', () => {
  const mockImage: Image = {
    id: 1,
    filename: 'test.jpg',
    filepath: '/test/path.jpg',
    filetype: 'image/jpeg',
    thumbnail_path: '/test/thumb.jpg',
    width: 1920,
    height: 1080,
    aspect_width: 16,
    aspect_height: 9
  };

  it('renders image filename and thumbnail', () => {
    render(<ArtItemCard item={mockImage} />);
    
    expect(screen.getByText('test.jpg')).toBeInTheDocument();
    expect(screen.getByRole('img')).toHaveAttribute('src', `/${mockImage.thumbnail_path}`);
  });

  it('has make active button that triggers API call', () => {
    const mockAxios = jest.spyOn(axios, 'post').mockResolvedValue({});
    render(<ArtItemCard item={mockImage} />);
    
    fireEvent.click(screen.getByLabelText(`Make ${mockImage.filename} active`));
    expect(mockAxios).toHaveBeenCalledWith(`/api/active-art/${mockImage.id}`);
  });

  it('opens dialog when settings button is clicked', () => {
    render(<ArtItemCard item={mockImage} />);
    
    fireEvent.click(screen.getByLabelText(`Settings for ${mockImage.filename}`));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });
});
