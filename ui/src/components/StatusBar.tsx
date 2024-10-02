import React from "react";
import { Paper, Stack } from "@mui/material";
import { styled } from '@mui/material/styles';

interface StatusBarProps {
    tv_on: boolean;
    art_mode_supported: boolean;
    art_mode_active: boolean;
    api_version: string
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

export default function StatusBar({tv_on, art_mode_supported, art_mode_active, api_version}: StatusBarProps) {
    return (
        <>
            <h2>Status</h2>
            <Stack direction="row" spacing={2}>
                <Item>TV: {tv_on ? "On" : "Off"}</Item>
                <Item>Art Mode: {art_mode_supported ? (art_mode_active ? "On" : "Off") : "Not Supported"}</Item>
                <Item>API Version: {api_version}</Item>
            </Stack>
        </>
    )
}