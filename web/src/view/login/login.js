import React, { useState } from 'react';
import { FormControl, TextField, Button } from '@material-ui/core';
import { AuthenticationService } from '../../services/authentication.service';

const Login = () => {
    let userCredentials = {
        username: '',
        password: '',
    };

    const [user, setUser] = useState(userCredentials);

    const handleChange = (e) => {
        e.preventDefault();
        setUser({
            ...user,
            [e.target.name]: e.target.value,
        });
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        new AuthenticationService().login(user).then((data) => {
            localStorage.setItem('jwt', JSON.stringify(data.access));
            window.location.href = '/';
        });
    };

    return (
        <div className='container-login'>
            <div className='wrapper'>
                <div className='mat-card'>
                    <h1>Sign In</h1>
                    <FormControl className='login-input'>
                        <TextField
                            className='item-card'
                            name='username'
                            onChange={handleChange}
                            variant='outlined'
                            label='Username'
                        />
                        <TextField
                            className='item-card'
                            name='password'
                            onChange={handleChange}
                            type='password'
                            variant='outlined'
                            label='Password'
                        />
                    </FormControl>
                    <div className='btn-submit'>
                        <Button onClick={handleSubmit} variant='contained' color='primary'>
                            Sign In
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Login;
