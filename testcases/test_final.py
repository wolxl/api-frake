import requests

Base_url="http://127.0.0.1:5000"
def test_final():


    data={
            "username":"admin",
            "password":"123456",
        }
    res=requests.post(f"{Base_url}/api/login",json=data)
    assert res.status_code == 200

    token=res.json()["token"]
    headers={
        "Authorization":f"Bearer {token}"
    }
    rre=requests.get(f"{Base_url}/api/books",headers=headers)
    assert rre.status_code == 200
