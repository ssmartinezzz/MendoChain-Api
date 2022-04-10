import { useState, useEffect } from 'react';
import { create } from '../services/transactionService';
import { getAll } from '../services/wineService.js';
import { Tablewine } from './Tablewine';
export const TransactionUpload = () => {
    const [wineList, setWineList] = useState([
        {
            id: 0,
            namewine: '',
        },
    ]);

    useEffect(() => {
        getAll().then((data) => {
            data.forEach((wl) =>
                setWineList({
                    id: wl.id,
                    namewine: wl.variety_name,
                })
            );
        });
    }, []);

    const [formValues, setFormValues] = useState({
        quantity: 0,
        transaction_id: 'asdfjs2322',
        wine: 1,
    });
    const { quantity, transaction_id, wine } = formValues;
    const handleSubmit = (e) => {
        e.preventDefault();
        const data = { transaction_id: transaction_id, quantity: parseInt(quantity), wine: wine };
        create(data);
        setFormValues({
            quantity: 0,
        });
        window.location.href = '/transaction';
    };

    const handleChange = (e) => {
        e.preventDefault();
        setFormValues({ ...formValues, [e.target.name]: e.target.value });
        console.log(formValues);
    };
    console.log(wineList.namewine);
    return (
        <div className=' vh-100  d-flex justify-content-center align-items-center'>
            <form onSubmit={handleSubmit}>
                {wineList.map(data => (
                    <Tablewine handleChange={handleChange} quantity={quantity} key={data.id} namewine={data.namewine}/>
                ))}
                
            </form>
        
        </div>
    );
};
