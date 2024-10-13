import React, { useState } from "react";
import { Paper, Stack, ToggleButton, ToggleButtonGroup } from "@mui/material";
import { styled } from '@mui/material/styles';

export interface SlideshowStatus {
    value: 'on'|'off';
    category_id: string;
    sub_category_id: string;
    current_content_id: string;
    type: string;
    content_list: string|Array<string>
}

export interface StatusBarProps {
    tv_on: boolean;
    art_mode_supported: boolean;
    art_mode_active: boolean;
    api_version: string;
    slideshow_status?: SlideshowStatus|null;
}

const Item = styled(Paper)(({ theme }) => ({
    backgroundColor: '#fff',
    ...theme.typography.body2,
    padding: theme.spacing(1),
    textAlign: 'center',
    color: theme.palette.text.secondary,
    ...theme.applyStyles('dark', {
        backgroundColor: '#1A2027',
    }),
}));


function StatusBar({tv_on, art_mode_supported, art_mode_active, api_version, slideshow_status}: StatusBarProps) {
    const [slideshowStatus, setSlideshowStatus] = useState(slideshow_status?.value ?? 'off');

    const toggleSlideshowStatus = (event: React.MouseEvent<HTMLElement>, newStatus: 'on'|'off') => {
        console.log("Toggling slideshow status to", newStatus);
        setSlideshowStatus(newStatus);
    };

    return (
        <>
            <Stack direction={"column"} spacing={2}>
                <div>
                    <h2>Status</h2>
                    <Stack direction="row" spacing={2}>
                        <Item>TV: {tv_on ? "On" : "Off"}</Item>
                        <Item>Art Mode: {art_mode_supported ? (art_mode_active ? "On" : "Off") : "Not Supported"}</Item>
                        <Item>API Version: {api_version}</Item>
                    </Stack>
                </div>
                <div>
                    <h2>Slideshow</h2>
                    Status: &nbsp;
                    <ToggleButtonGroup
                        exclusive
                        onChange={toggleSlideshowStatus}
                        aria-label="Slideshow"
                        value={slideshowStatus}
                    >
                        <ToggleButton value="on">On</ToggleButton>
                        <ToggleButton value="off">Off</ToggleButton>
                    </ToggleButtonGroup>
                </div>
            </Stack>
        </>
    )
}

export default StatusBar;