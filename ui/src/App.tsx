import React, { useEffect, useState } from 'react';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import StatusBar, { StatusBarProps } from "./components/StatusBar";
import axios from "axios";
import ImageGrid from "./components/ImageGrid";
import ArtItem from "./models/ArtItem";

export default function App() {
    const [status, setStatus] = useState<StatusBarProps>({tv_on: false, art_mode_supported: false, art_mode_active: false, api_version: '', slideshow_status: null});

    const [items, setItems] = useState<ArtItem[]>([]);

    useEffect(() => {
        const fetchStatus = async () => {
            const url = 'http://localhost:7999/api/status';

            try {
                const response = await axios.get(url);
                setStatus(response.data);
            } catch (error) {
                console.error(error);
            }
        };
        fetchStatus();
    }, []); // The empty dependency array ensures the effect runs only once

    useEffect(() => {
        const fetchItems = async () => {
            const url = 'http://localhost:7999/api/available-art';

            try {
                const response = await axios.get(url);
                setItems(response.data);
            } catch (error) {
                console.error(error);
            }
        };
        fetchItems();
    }, []);

    return (
        <Container maxWidth="xl">
            <Box sx={{my: 4}}>
                <Typography variant="h4" component="h1" sx={{mb: 2, px: 50}}>
                    The Frame Art Gallery Manager
                </Typography>
            </Box>
            <Container sx={{mb: 10}}>
                <StatusBar tv_on={status.tv_on}
                           api_version={status.api_version}
                           art_mode_active={status.art_mode_active}
                           art_mode_supported={status.art_mode_supported}
                />
            </Container>
            <ImageGrid items={items}/>
        </Container>
    );
}
