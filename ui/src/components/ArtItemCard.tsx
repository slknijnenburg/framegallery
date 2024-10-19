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
import SettingsIcon from '@mui/icons-material/Settings';
import axios from "axios";
import { IconButton, IconButtonProps } from "@mui/material";
import { styled } from "@mui/material/styles";

export interface ArtItemCardProps {
    item: ArtItem;
}


interface ExpandMoreProps extends IconButtonProps {
    expand: boolean;
}

const ExpandMore = styled((props: ExpandMoreProps) => {
    const { expand, ...other } = props;
    return <IconButton {...other} />;
})(({ theme }) => ({
    marginLeft: 'auto',
    transition: theme.transitions.create('transform', {
        duration: theme.transitions.duration.shortest,
    }),
}));

const RightSettings = styled((props) => {
    return <IconButton {...props} />;
})(({ theme }) => ({
    marginLeft: 'auto',
}));

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
                <IconButton aria-label={`Make ${item.thumbnail_filename} active`} onClick={makeActiveArt}>
                    <VisibilityIcon/>
                </IconButton>

                <IconButton aria-label={`Delete ${item.thumbnail_filename} from TV`}>
                    <DeleteIcon/>
                </IconButton>

                <ExpandMore expand={true} aria-label={`Expand ${item.thumbnail_filename}`}>
                    <SettingsIcon />
                </ExpandMore>

                {/*<RightSettings aria-label={`Settings for ${item.thumbnail_filename}`} >*/}
                {/*    <SettingsIcon/>*/}
                {/*</RightSettings>*/}
            </CardActions>
        </Card>
    );
}