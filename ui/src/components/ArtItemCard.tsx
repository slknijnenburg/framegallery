import ArtItem from "../models/ArtItem";
import LoadingButton from '@mui/lab/LoadingButton';
import Card from '@mui/material/Card';
import CardActions from '@mui/material/CardActions';
import CardContent from '@mui/material/CardContent';
import CardMedia from '@mui/material/CardMedia';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import VisibilityIcon from '@mui/icons-material/Visibility';
import DeleteIcon from '@mui/icons-material/Delete';
import axios from "axios";

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


    return (
        <Card sx={{maxWidth: 345}}>
            <CardMedia
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
                <Button variant="contained"
                        startIcon={<VisibilityIcon/>}
                        size="small"
                        onClick={makeActiveArt}
                >
                    View
                </Button>
                <LoadingButton
                    loadingPosition="start"
                    startIcon={<DeleteIcon/>}
                    variant="outlined"
                    size="small"
                >
                    Remove
                </LoadingButton>
            </CardActions>
        </Card>
    );
}