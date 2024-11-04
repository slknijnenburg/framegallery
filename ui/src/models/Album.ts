/** Album is a container for images, referencing a path in the gallery folder. */
export interface Album {
    id: string;
    name: string;
    label: string;
    children: Array<Album>;
}

export const findAlbumById = (albums: Album[], id: string | null): Album | null => {
    for (const album of albums) {
        if (album.id === id) {
            return album;
        }
        const foundInChildren = findAlbumById(album.children, id);
        if (foundInChildren) {
            return foundInChildren;
        }
    }
    return null;
};
