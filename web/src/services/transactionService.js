import axios from 'axios';
import { SettingsService } from './settings.service';
import { apiUrl } from './settings.service';

    export const getAll = async () => {
        const query = await axios.get(`${apiUrl}/api/transaction`, {
            headers: {
                'Content-Type': 'application/json',
            },
        });

        return query.data;
    }

    export const deleteTransaction = async (id) => {
        const query = await axios.delete(`${apiUrl}/api/transaction/${id}`, {
            headers: {
                'Content-Type': 'application/json',
            },
        });

        return query.data;
    }

    export const create = async (data) =>{
        data = JSON.stringify(data);
        const query = await axios.post(`${apiUrl}/api/transaction`, data, {
            headers: {
                'Content-Type': 'application/json',
            },
        });
        return query.data;
    }

