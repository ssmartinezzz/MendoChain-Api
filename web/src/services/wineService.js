import axios from 'axios';
import { apiUrl } from './settings.service';



export const getAll = async () => {
        const query = await axios.get(`${apiUrl}/api/wine`, {
            headers: {
                'Content-Type': 'application/json',
            },
        });
        return query.data;
    }

    export const deleteWine = async (id) =>  {
        const query = await axios.delete(`${apiUrl}/api/wine/${id}`, {
            headers: {
                'Content-Type': 'application/json',
            },
        });

        return query.data;
    }
export const createWine = async (wine) =>{
        wine = JSON.stringify(wine);
        const query = await axios.post(`${apiUrl}/api/wine`, wine, {
            headers: {
                'Content-Type': 'application/json',    
            },
        }).then(function (error){
            console.log(error);
        }).catch(function (error){
            console.log(error);
        });
        console.log(query.data);
        return query.data;
    }

