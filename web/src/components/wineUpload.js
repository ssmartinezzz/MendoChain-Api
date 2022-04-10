import React, { useState } from 'react';
import { FormControl, TextField, Button } from '@material-ui/core';
import { createWine } from '../services/wineService.js';

const WineUpload = () => {
    let wineModel = {
        variety_name: '',
        content: '',
        alcohol: '',
        brand_name: '',
        lote: '',
    };

    const [wine, uploadWine] = useState(wineModel);

    const handleChange = (e) => {
        e.preventDefault();
        uploadWine({
            ...wine,
            [e.target.name]: e.target.value,
        });
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        createWine(wine);
	window.location.href = '/wine';
    };

    return (
        <div className='container-register'>
            <div className='wrapper'>
                <div className='mat-card'>
                    <h1>Upload a product</h1>
                    <FormControl className='login-input'>
                        <TextField
                            className='item-card'
                            name='variety_name'
                            type='text'
                            variant='outlined'
                            onChange={handleChange}
                            label='Variety'
                        />
                        <TextField
                            className='item-card'
                            name='content'
                            type='text'
                            variant='outlined'
                            onChange={handleChange}
                            label='Content'
                        />
                        <TextField
                            className='item-card'
                            name='alcohol'
                            type='text'
                            variant='outlined'
                            onChange={handleChange}
                            label='Alcohol'
                        />
                        <TextField
                            className='item-card'
                            name='brand_name'
                            type='text'
                            variant='outlined'
                            onChange={handleChange}
                            label='Brand Name'
                        />
                        <TextField
                            className='item-card'
                            name='lote'
                            type='text'
                            variant='outlined'
                            onChange={handleChange}
                            label='lote'
                        />
                    </FormControl>
                    <div className='btn-submit'>
                        <Button onClick={handleSubmit} variant='contained' color='primary'>
                            Upload
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default WineUpload;
