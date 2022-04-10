import { Button } from '@material-ui/core';
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { HelloWorldService } from '../../services/hello-world.service';
import './home.css';

const Home = () => {
    const [userName, setUserName] = useState('');

    useEffect(() => {
        new HelloWorldService().showHelloWorld().then((data) => {
            setUserName(data.username);
        });
    }, []);

    const logout = (event) => {
        event.preventDefault();
        localStorage.removeItem('jwt');
        window.location.href = '/';
    };

    return (
        <div className='home'>
            <div className='home__info-container'>
                <h1 className='home__title'>Hello world {userName ? userName : 'Anonymous'}!</h1>
                {!userName ? (
                    <div>
                        <Link to='/signin'>
                            <Button color='secondary'>Signin</Button>
                        </Link>
                        <Link to='/signup'>
                            <Button variant='contained' color='primary'>
                                Signup
                            </Button>
                        </Link>
                    </div>
                ) : (
                    <div>
                        <Button onClick={logout} variant='contained' color='primary'>
                            Logout
                        </Button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Home;
