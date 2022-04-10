import { BrowserRouter, Switch, Route } from 'react-router-dom';
import Home from './view/home/home';
import Login from './view/login/login';
import Register from './view/register/register';
import WineList from './components/wineList';
import Wine from './components/wine';
import wineUpload from './components/wineUpload';
import TransactionList from './components/transactionList';
import { TransactionUpload } from './components/transactionUpload';
import NotFound from './view/errors/404-not-found';

import './App.css';




function App() {
    return (
        <div>
            <BrowserRouter>
                <Switch>
                    <Route exact path='/' component={Home} />
                    <Route exact path='/signin' component={Login} />
                    <Route exact path='/signup' component={Register} />
                    <Route exact path='/wine' component={WineList} />
                    <Route exact path='/wine/upload' component={wineUpload}/>
                    <Route exact path='/transaction' component={TransactionList} />
                    <Route exact path='/transaction/upload' component={TransactionUpload} />
                    <Route path='/*' component={NotFound} />
                </Switch>
            </BrowserRouter>
        </div>
    );
}

export default App;
