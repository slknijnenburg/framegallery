import ArtItem from "../models/ArtItem";
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

export interface ArtItemCardProps {
    item: ArtItem;
}

export default function ArtItemCard({item}: ArtItemCardProps) {
    // Create function to POST to the API to make this art active, that will be called when the button is clicked
    const makeActiveArt = async () => {
        try {
            await axios.post(`http://localhost:7999/api/active-art/${item.content_id}`);
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
                image={`data:image/jpeg;base64,${item.thumbnail_data}`}
                title={item.thumbnail_filename}
            />
            <CardContent>
                <Typography gutterBottom variant="h5" component="div">
                    {item.thumbnail_filename}
                </Typography>
            </CardContent>
            <CardActions>
                <IconButton aria-label={`Make ${item.thumbnail_filename} active`} onClick={makeActiveArt}>
                    <VisibilityIcon/>
                </IconButton>

                <IconButton aria-label={`Delete ${item.thumbnail_filename} from TV`}>
                    <DeleteIcon/>
                </IconButton>

                <IconButton aria-label={`Settings for ${item.thumbnail_filename}`} onClick={openDialog}>
                    <SettingsIcon/>
                </IconButton>
                <ArtItemDialog open={dialogOpened} artItem={item} onClose={closeDialog}/>
            </CardActions>
        </Card>
    );
}