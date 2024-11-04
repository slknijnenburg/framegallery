import Card from '@mui/material/Card';
import CardActions from '@mui/material/CardActions';
import CardContent from '@mui/material/CardContent';
import CardMedia from '@mui/material/CardMedia';
import Typography from '@mui/material/Typography';
import VisibilityIcon from '@mui/icons-material/Visibility';
import DeleteIcon from '@mui/icons-material/Delete';
import SettingsIcon from '@mui/icons-material/Settings';
import axios from "axios";
import { IconButton } from "@mui/material";
import ArtItemDialog from "./ArtItemDialog";
import { useState } from "react";
import Image from "../models/Image";
import { API_BASE_URL } from "../App";

export interface ArtItemCardProps {
    item: Image;
}

export default function ArtItemCard({item}: ArtItemCardProps) {
    // Create function to POST to the API to make this art active, that will be called when the button is clicked
    const makeActiveArt = async () => {
        try {
            await axios.post(`http://localhost:7999/api/active-art/${item.id}`);
        } catch (error) {
            console.error(error);
        }
    };

    const [dialogOpened, setDialogOpened] = useState(false);

    // console.log("ArtItemCard matte_id = ", item.matte_id);

    const openDialog = (): void => {
        setDialogOpened(true);
    }
    const closeDialog = (): void => {
        setDialogOpened(false);
    }

    return (
        <Card sx={{maxWidth: 345}}>
            <CardMedia
                component='img'
                sx={{height: 140}}
                image={`${API_BASE_URL}${item.thumbnail_path}`}
                title={item.filename}
            />
            <CardContent>
                <Typography gutterBottom variant="body2" component="span">
                    {item.filename}
                </Typography>
            </CardContent>
            <CardActions>
                <IconButton aria-label={`Make ${item.filename} active`} onClick={makeActiveArt}>
                    <VisibilityIcon/>
                </IconButton>

                <IconButton aria-label={`Delete ${item.filename} from TV`}>
                    <DeleteIcon/>
                </IconButton>

                <IconButton aria-label={`Settings for ${item.filename}`} onClick={openDialog}>
                    <SettingsIcon/>
                </IconButton>
                <ArtItemDialog open={dialogOpened} image={item} onClose={closeDialog}/>
            </CardActions>
        </Card>
    );
}