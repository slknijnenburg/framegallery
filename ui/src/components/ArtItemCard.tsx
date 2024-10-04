import ArtItem from "../models/ArtItem";
import Card from '@mui/material/Card';
import CardActions from '@mui/material/CardActions';
import CardContent from '@mui/material/CardContent';
import CardMedia from '@mui/material/CardMedia';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';

export interface ArtItemCardProps {
    item: ArtItem;
}
export default function ArtItemCard({item}: ArtItemCardProps) {
    return (
        <Card sx={{ maxWidth: 345 }}>
            <CardMedia
                sx={{ height: 140 }}
                image={`data:image/jpeg;base64,${item.thumbnail_data}`}
                title={item.thumbnail_filename}
            />
            <CardContent>
                <Typography gutterBottom variant="h5" component="div">
                    {item.thumbnail_filename}
                </Typography>
            </CardContent>
            <CardActions>
                <Button size="small">Make active</Button>
                <Button size="small">Remove</Button>
            </CardActions>
        </Card>
    );
}