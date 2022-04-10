import axios from 'axios';
import { apiUrl } from './settings.service';

export class AuthenticationService{
    async register(user) {
        user = JSON.stringify(user);

        const query = await axios.post(`${apiUrl}/auth/users`, user, {
            headers: {
                'Content-Type': 'application/json',
            },
        });

        return query.data;
    }

    async login(userCredentials) {
        userCredentials = JSON.stringify(userCredentials);

        const query = await axios.post(`${apiUrl}/login`, userCredentials, {
            headers: {
                'Content-Type': 'application/json',
            },
        });

        return query.data;
    }

    async showCurrentUser() {
        const jwt = JSON.parse(localStorage.getItem('jwt'));

        const query = await axios.get(`${apiUrl}/auth/current_user`, {
            headers: {
                'Content-Type': 'application/json',

                Authorization: `Bearer ${jwt['jwt']}`,
            },
        });

        return query.data;
    }
}
